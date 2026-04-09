from langchain_core.runnables import Runnable
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.callbacks import dispatch_custom_event
from loguru import logger

from backend.agents.deep_research_agent.state import DeepResearchAgentState
from backend.utils.llm import azure_chat_openai_gpt_5_1


service_logger = logger.bind(service="deep-research-synthesize")


SYNTHESIZE_SYSTEM = """You are an expert research synthesizer. Create comprehensive, well-structured reports from research findings.

Guidelines:
1. Organize findings logically under clear headings
2. Synthesize information from multiple sources
3. Cite sources using [1], [2], etc. notation
4. Highlight key insights and discoveries
5. Acknowledge any limitations or uncertainties
6. Provide actionable conclusions
7. Use clear, professional language"""


SYNTHESIZE_USER = """Synthesize a comprehensive research report:

Original Question: {user_question}

Research Findings:
{findings_text}

Create a well-structured report that:
1. Directly answers the research question
2. Organizes findings under relevant headings
3. Cites sources appropriately
4. Highlights key insights
5. Notes any limitations

Format the report in clear markdown."""


class SynthesizeNode(Runnable):
    def __init__(self):
        super().__init__()

    def invoke(self, state: DeepResearchAgentState, **kwargs):
        pass

    async def ainvoke(self, state: DeepResearchAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_synthesize",
                "message": "📝 Synthesizing research findings...",
            },
        )

        findings_text = ""
        for i, finding in enumerate(state.findings):
            findings_text += f"\n### Finding {i + 1}: {finding.topic}\n"
            findings_text += f"Key Facts:\n"
            for fact in finding.key_facts:
                findings_text += f"- {fact}\n"
            if finding.sources:
                findings_text += f"\nSources: {', '.join(finding.sources)}\n"
            findings_text += f"\nConfidence: {finding.confidence:.0%}\n"
        
        search_summary = ""
        if state.search_results:
            search_summary = f"\n\nAnalyzed {len(state.search_results)} sources across {state.max_iterations} iterations."

        messages = [
            SystemMessage(content=SYNTHESIZE_SYSTEM),
            HumanMessage(content=SYNTHESIZE_USER.format(
                user_question=state.user_question,
                findings_text=findings_text[:6000],
            )),
        ]

        service_logger.info("Synthesizing final report")

        response = await azure_chat_openai_gpt_5_1.ainvoke(messages)
        final_report = response.content

        final_report += search_summary

        service_logger.info(f"Final report synthesized: {len(final_report)} characters")

        dispatch_custom_event(
            "status",
            {
                "step": "deep_research_synthesize",
                "message": "✅ Research report complete.",
            },
        )

        return {
            "final_report": final_report,
        }