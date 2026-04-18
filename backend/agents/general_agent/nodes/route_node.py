import re
import unicodedata

from langchain_core.callbacks import dispatch_custom_event
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from loguru import logger
from pydantic import BaseModel, Field

from backend.agents.general_agent.state import GeneralAgentState
from backend.agents.prompts.routing import ROUTE_SYSTEM_MESSAGE, ROUTE_USER_MESSAGE
from backend.utils.llm import azure_chat_openai_gpt_5_1


class RouteResponse(BaseModel):
    route: str = Field(
        description="The exact route to take: 'websearch_agent', 'direct_response', 'deep_research_agent', or 'image_generation_agent'"
    )
    confidence: float = Field(
        default=0.9,
        description="Confidence level 0.0-1.0 for this routing decision",
    )
    reasoning: str = Field(
        default="",
        description="Brief reasoning for why this route was selected",
    )
    detected_language: str = Field(
        default="auto",
        description="Detected language of the user question: 'vi', 'en', or 'auto'",
    )


VALID_ROUTES = {
    "websearch_agent",
    "direct_response",
    "deep_research_agent",
    "image_generation_agent",
}
SPECIALIZED_ROUTES = VALID_ROUTES - {"direct_response"}
MANUAL_ROUTE_PREFERENCES = SPECIALIZED_ROUTES | {"auto"}

EXPLICIT_WEBSEARCH_PATTERNS = (
    r"\bweb search\b",
    r"\bsearch\b",
    r"\bsearch the web\b",
    r"\bsearch online\b",
    r"\blook up\b",
    r"\btra cuu\b",
    r"\btim kiem\b",
    r"\btim tren web\b",
    r"\bthuc hien web search\b",
    r"\bcap nhat\b",
    r"\bkiem chung\b",
    r"\bverify\b",
    r"\bfact check\b",
)
WEBSEARCH_DYNAMIC_PATTERNS = (
    r"\blatest\b",
    r"\brecent\b",
    r"\bcurrent\b",
    r"\btoday\b",
    r"\btomorrow\b",
    r"\bthis week\b",
    r"\bnews\b",
    r"\bprice\b",
    r"\bweather\b",
    r"\bwho is\b",
    r"\bcurrent president\b",
    r"\bhien tai\b",
    r"\bmoi nhat\b",
    r"\bhom nay\b",
    r"\bngay mai\b",
    r"\btin tuc\b",
    r"\bgia\b",
    r"\bty gia\b",
)
EXPLICIT_DEEP_RESEARCH_PATTERNS = (
    r"\bdeep research\b",
    r"\bresearch about\b",
    r"\bresearch on\b",
    r"\bdeep dive\b",
    r"\bcomprehensive analysis\b",
    r"\bdetailed report\b",
    r"\bnghien cuu sau\b",
    r"\bphan tich sau\b",
    r"\btim hieu ky\b",
    r"\bbao cao chi tiet\b",
)
DEEP_RESEARCH_BROAD_PATTERNS = (
    r"\bnghien cuu\b",
    r"\bphan tich\b",
    r"\bthi truong\b",
    r"\bmarket\b",
    r"\bxu huong\b",
    r"\btrend\b",
    r"\boutlook\b",
    r"\bforecast\b",
    r"\broadmap\b",
    r"\blandscape\b",
    r"\bcompare\b",
    r"\bcomparison\b",
    r"\bso sanh\b",
    r"\brisk\b",
    r"\brisks\b",
    r"\bopportunity\b",
    r"\bopportunities\b",
    r"\bbao cao\b",
    r"\breport\b",
    r"\bchien luoc\b",
    r"\bstrategy\b",
    r"\btuong lai\b",
    r"\bfuture\b",
)
EXPLICIT_IMAGE_PATTERNS = (
    r"\bgenerate image\b",
    r"\bcreate image\b",
    r"\bdraw\b",
    r"\bmake an image\b",
    r"\btao anh\b",
    r"\btao hinh\b",
    r"\billustration\b",
    r"\blogo\b",
)
YEAR_PATTERN = re.compile(r"\b20\d{2}\b")


class RouteNode(Runnable):
    def __init__(self) -> None:
        super().__init__()

    def invoke(self, state: GeneralAgentState, **kwargs):
        pass

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text or "")
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        normalized = re.sub(r"\s+", " ", normalized).strip().lower()
        return normalized

    @staticmethod
    def _matches_any_pattern(question: str, patterns: tuple[str, ...]) -> bool:
        return any(re.search(pattern, question, flags=re.IGNORECASE) for pattern in patterns)

    @staticmethod
    def _count_pattern_matches(question: str, patterns: tuple[str, ...]) -> int:
        return sum(1 for pattern in patterns if re.search(pattern, question, flags=re.IGNORECASE))

    @staticmethod
    def _is_deep_research_manually_requested(state: GeneralAgentState) -> bool:
        return (state.route_preference or "auto").strip() == "deep_research_agent"

    @classmethod
    def _is_route_enabled(cls, state: GeneralAgentState, route: str) -> bool:
        return {
            "websearch_agent": state.is_web_search_enabled,
            "deep_research_agent": state.is_deep_research_enabled and cls._is_deep_research_manually_requested(state),
            "image_generation_agent": state.is_generate_image_enabled,
            "direct_response": True,
        }.get(route, False)

    def _resolve_manual_preference(self, state: GeneralAgentState) -> str | None:
        route_preference = (state.route_preference or "auto").strip()
        if route_preference not in MANUAL_ROUTE_PREFERENCES or route_preference == "auto":
            return None
        return route_preference

    def _calculate_scores(self, question: str) -> dict[str, int]:
        websearch_score = self._count_pattern_matches(question, WEBSEARCH_DYNAMIC_PATTERNS)
        deep_research_score = self._count_pattern_matches(question, DEEP_RESEARCH_BROAD_PATTERNS)
        image_score = self._count_pattern_matches(question, EXPLICIT_IMAGE_PATTERNS)

        has_year = bool(YEAR_PATTERN.search(question))
        if has_year:
            websearch_score += 1
            if self._matches_any_pattern(question, (r"\bxu huong\b", r"\btrend\b", r"\bfuture\b", r"\btuong lai\b", r"\bmarket\b", r"\bthi truong\b")):
                deep_research_score += 1

        return {
            "websearch_agent": websearch_score,
            "deep_research_agent": deep_research_score,
            "image_generation_agent": image_score,
        }

    def _resolve_disabled_route(
        self,
        state: GeneralAgentState,
        route: str,
        scores: dict[str, int],
    ) -> str:
        if route == "deep_research_agent":
            if self._is_route_enabled(state, "websearch_agent") and (
                scores["websearch_agent"] > 0 or scores["deep_research_agent"] > 0
            ):
                return "websearch_agent"
            return "direct_response"

        if route == "websearch_agent":
            return "direct_response"

        if route == "image_generation_agent":
            return "direct_response"

        return "direct_response"

    def _heuristic_route(self, state: GeneralAgentState) -> tuple[str | None, str]:
        question = self._normalize_text(state.user_question)
        if not question:
            return None, "empty_question"

        manual_preference = self._resolve_manual_preference(state)
        scores = self._calculate_scores(question)

        if manual_preference:
            route = (
                manual_preference
                if self._is_route_enabled(state, manual_preference)
                else self._resolve_disabled_route(state, manual_preference, scores)
            )
            return route, f"manual_preference:{manual_preference}"

        if self._matches_any_pattern(question, EXPLICIT_IMAGE_PATTERNS):
            route = (
                "image_generation_agent"
                if self._is_route_enabled(state, "image_generation_agent")
                else self._resolve_disabled_route(state, "image_generation_agent", scores)
            )
            return route, "explicit_image_intent"

        if self._matches_any_pattern(question, EXPLICIT_WEBSEARCH_PATTERNS):
            route = (
                "websearch_agent"
                if self._is_route_enabled(state, "websearch_agent")
                else self._resolve_disabled_route(state, "websearch_agent", scores)
            )
            return route, "explicit_websearch_intent"

        if self._matches_any_pattern(question, EXPLICIT_DEEP_RESEARCH_PATTERNS):
            return self._resolve_disabled_route(state, "deep_research_agent", scores), "explicit_deep_research_intent"

        if scores["image_generation_agent"] >= 1 and self._is_route_enabled(state, "image_generation_agent"):
            return "image_generation_agent", "image_heuristic"

        if scores["deep_research_agent"] >= 3 and (
            scores["deep_research_agent"] >= scores["websearch_agent"]
        ):
            return self._resolve_disabled_route(state, "deep_research_agent", scores), "deep_research_heuristic"

        if scores["websearch_agent"] >= 2:
            route = (
                "websearch_agent"
                if self._is_route_enabled(state, "websearch_agent")
                else self._resolve_disabled_route(state, "websearch_agent", scores)
            )
            return route, "websearch_heuristic"

        return None, "llm_required"

    async def _llm_route(self, state: GeneralAgentState) -> tuple[str, float, str]:
        system_prompt = ROUTE_SYSTEM_MESSAGE.format(
            is_web_search_enabled=state.is_web_search_enabled,
            is_deep_research_enabled=state.is_deep_research_enabled,
            is_generate_image_enabled=state.is_generate_image_enabled,
        )

        messages = [
            SystemMessage(content=system_prompt),
            *state.memories,
            HumanMessage(content=ROUTE_USER_MESSAGE.format(user_question=state.user_question)),
        ]

        logger.info(f"RouteNode evaluating question with LLM fallback: '{state.user_question}'")
        llm_with_structured_output = azure_chat_openai_gpt_5_1.with_structured_output(RouteResponse)
        response = await llm_with_structured_output.ainvoke(messages)
        route = response.route if response.route in VALID_ROUTES else "direct_response"
        return route, response.confidence, response.reasoning

    async def ainvoke(self, state: GeneralAgentState, **kwargs):
        dispatch_custom_event(
            "status",
            {"step": "routing", "message": "Analyzing the request and selecting the best route..."},
        )

        heuristic_route, heuristic_reason = self._heuristic_route(state)
        if heuristic_route:
            logger.info(f"RouteNode selected heuristic route: {heuristic_route} ({heuristic_reason})")
            dispatch_custom_event(
                "status",
                {
                    "step": "routing",
                    "message": f"Selected route: {heuristic_route}",
                },
            )
            return {"route": heuristic_route}

        route, confidence, reasoning = await self._llm_route(state)
        scores = self._calculate_scores(self._normalize_text(state.user_question))
        if not self._is_route_enabled(state, route):
            route = self._resolve_disabled_route(state, route, scores)
            confidence = max(confidence, 0.6)

        if confidence < 0.4 and route != "direct_response":
            logger.info(f"RouteNode confidence too low ({confidence:.2f}), falling back to direct_response")
            route = "direct_response"

        logger.info(
            f"RouteNode decided route: {route} (confidence: {confidence:.2f}, reason: {reasoning[:100]})"
        )
        dispatch_custom_event(
            "status",
            {
                "step": "routing",
                "message": f"Selected route: {route}",
            },
        )
        return {"route": route}
