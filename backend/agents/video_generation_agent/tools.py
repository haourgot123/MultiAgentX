from typing import Any

from langchain.tools import tool


VIDEO_IMAGE_SEARCH_TOOL_DESCRIPTION = """
Search the web for high-quality scene images, review candidates with a vision model,
mirror approved images to blob storage, and attach the approved image URLs to storyboard scenes.

Use this when a video needs livelier visuals from the internet. Reject blurry, text-heavy,
poster-like, infographic-like, logo-only, UI screenshot, or irrelevant images.
"""


@tool(description=VIDEO_IMAGE_SEARCH_TOOL_DESCRIPTION)
async def video_image_search(query: str) -> dict[str, Any]:
    """Tool contract for the video generation agent.

    The LangGraph AssetNode owns the runtime implementation because it needs access to
    job_id, user_id, storyboard scenes, blob storage, and vision review. This tool
    exists so downstream agent prompts can explicitly reason about the available
    image-search capability and its output contract.
    """
    return {
        "query": query,
        "status": "handled_by_asset_node",
        "output_contract": {
            "scene.image_url": "approved blob/SAS image URL or null",
            "remotion_input.assetReferences": "per-scene image metadata for code generation",
        },
    }


VIDEO_GENERATION_TOOLS = [video_image_search]
