from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger
import re

from backend.agents.deep_research_agent.state import DeepResearchAgentState, Tag, SearchResult
from backend.utils.llm import azure_chat_openai_gpt_5_1
from backend.agents.prompts.deep_research import DEEP_RESEARCH_PROMPTS


service_logger = logger.bind(service="deep-research-synthesize")


SYNTHESIZE_USER = """Synthesize a comprehensive research report:

Original Question: {user_question}

## Research Methodology
- Total iterations: {total_iterations}
- Total sources analyzed: {total_sources}
- Sub-questions investigated: {sub_questions}

## Research Findings by Iteration:
{findings_text}

## Source References (use these URLs to create inline citations like [1], [2], [3]):
{sources_text}

## Research Plan Coverage:
{coverage_text}

## Instructions:
1. Create a comprehensive report following the structure in your system instructions
2. Start with an executive summary (2-3 paragraphs)
3. Organize findings into 3-5 thematic sections with clear headings
4. Use inline numeric citations like [1], [2], [3] immediately after key claims — the number must match the source references above
5. Include specific data, statistics, and examples from the findings
6. Acknowledge limitations and any conflicting information
7. End with clear conclusions and recommendations
8. Add a "## Sources" section at the end with numbered markdown links in this exact format:
   [1] [Source Title](URL)
   [2] [Another Source](URL)

Format: Use markdown with proper headings, bullet points, and emphasis.
Language: Match the language of the original question ({detected_language}).
Citations: Be selective — cite important claims, not every sentence."""


class SynthesizeNode(Runnable):
    SOURCES_SECTION_REGEX = re.compile(
        r"(?:^|\n)(?:#{1,6}\s+)?(?:\d+(?:\.\d+)*\.?\s+)?(?:Sources|References|Nguon|Nguồn|Tai lieu tham khao|Tài liệu tham khảo)\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    def __init__(self):
        super().__init__()

    @staticmethod
    def _build_sources_index(search_results: list[SearchResult]) -> list[tuple[str, str, str]]:
        ordered_sources: list[tuple[str, str, str]] = []
        seen_urls: set[str] = set()

        for result in search_results:
            if not result.url or result.url in seen_urls:
                continue

            seen_urls.add(result.url)
            ordered_sources.append(
                (
                    result.url,
                    (result.title or "Source").strip(),
                    (result.snippet or "").strip(),
                )
            )

        return ordered_sources

    @classmethod
    def _strip_existing_sources_section(cls, report: str) -> str:
        if not report:
            return report

        matches = list(cls.SOURCES_SECTION_REGEX.finditer(report))
        if not matches:
            return report.rstrip()

        return report[:matches[-1].start()].rstrip()

    @staticmethod
    def _append_canonical_sources_section(
        report_body: str, sources_index: list[tuple[str, str, str]]
    ) -> str:
        if not sources_index:
            return report_body.rstrip()

        sources_lines = [
            f"[{idx}] [{title}]({url})"
            for idx, (url, title, _snippet) in enumerate(sources_index, 1)
        ]
        return f"{report_body.rstrip()}\n\n## Sources\n" + "\n".join(sources_lines)

    def invoke(self, state: DeepResearchAgentState, **kwargs):
        pass

    async def ainvoke(self, state: DeepResearchAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_synthesize",
                "message": "Synthesizing comprehensive research report...",
            },
        )

        # Build detailed findings text
        findings_text = ""
        for i, finding in enumerate(state.findings):
            findings_text += f"\n### Finding {i + 1}: {finding.topic}\n"
            findings_text += f"**Confidence:** {finding.confidence:.0%}\n"
            findings_text += f"**Key Facts:**\n"
            for fact in finding.key_facts:
                findings_text += f"- {fact}\n"
            if finding.sources:
                findings_text += f"\n**Sources Used:** {', '.join(finding.sources[:3])}\n"
        
        # Build deduplicated sources text with proper numbering
        sources_index = self._build_sources_index(state.search_results)
        
        sources_text = ""
        for idx, (url, title, snippet) in enumerate(sources_index, 1):
            sources_text += f"\n[{idx}] Title: {title}\n"
            sources_text += f"    URL: {url}\n"
            if snippet:
                sources_text += f"    Key Info: {snippet[:250]}...\n"
        
        # Coverage analysis for the synthesis
        covered_topics = set()
        for finding in state.findings:
            covered_topics.add(finding.topic.strip())
        
        coverage_text = ""
        for i, question in enumerate(state.research_plan):
            is_covered = any(question.strip().lower() in t.lower() or t.lower() in question.strip().lower() for t in covered_topics)
            status = "✅ Covered" if is_covered else "❌ Not fully covered"
            coverage_text += f"{i+1}. {question} — {status}\n"

        # Detect language for the report
        detected_language = "Vietnamese" if any(
            c in state.user_question for c in "àáảãạèéẻẽẹìíỉĩịòóỏõọùúủũụỳýỷỹỵđ"
        ) else "English"

        # Sub-questions display
        sub_questions = "\n".join([f"  {i+1}. {q}" for i, q in enumerate(state.research_plan)])

        messages = [
            SystemMessage(content=DEEP_RESEARCH_PROMPTS["SYNTHESIZE_SYSTEM"]),
            HumanMessage(content=SYNTHESIZE_USER.format(
                user_question=state.user_question,
                total_iterations=state.current_iteration,
                total_sources=len(sources_index),
                sub_questions=sub_questions,
                findings_text=findings_text[:8000],
                sources_text=sources_text[:5000],
                coverage_text=coverage_text,
                detected_language=detected_language,
            )),
        ]

        service_logger.info(
            f"Synthesizing final report: {len(state.findings)} findings, "
            f"{len(sources_index)} unique sources, {state.current_iteration} iterations"
        )

        # Stream tokens natively using tagged config so the outer graph's
        # astream_events captures on_chat_model_stream events in real-time.
        llm_with_config = azure_chat_openai_gpt_5_1.with_config(
            {"tags": [Tag.streaming_node.name]}
        )

        full_output = ""
        async for chunk in llm_with_config.astream(messages):
            content = getattr(chunk, "content", None)
            if not content:
                continue
            full_output += content

        # Replace any model-generated sources block with a canonical markdown list
        # so the frontend can always resolve numeric citations to real URLs.
        full_output = self._strip_existing_sources_section(full_output)

        # Append research metadata summary
        metadata_summary = (
            f"\n\n---\n*Research completed: {state.current_iteration} iteration(s), "
            f"{len(sources_index)} sources analyzed, {len(state.findings)} finding groups.*"
        )
        full_output += metadata_summary
        full_output = self._append_canonical_sources_section(full_output, sources_index)

        service_logger.info(f"Final report synthesized: {len(full_output)} characters")

        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_synthesize",
                "message": "Research report complete.",
            },
        )

        return {
            "final_report": full_output,
            "output": full_output,
        }
