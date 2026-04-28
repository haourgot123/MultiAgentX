import pytest

import backend.agents.video_generation_agent.nodes.validate_settings_node as validate_module
from backend.agents.video_generation_agent.nodes.storyboard_node import StoryboardNode
from backend.agents.video_generation_agent.nodes.validate_settings_node import (
    ValidateSettingsNode,
)
from backend.agents.video_generation_agent.state import VideoGenerationAgentState


def make_state(**overrides):
    values = {
        "job_id": 1,
        "user_id": 1,
        "prompt": "Create a video about multi-agent systems",
        "duration_seconds": 30,
        "fps": 30,
        "aspect_ratio": "16:9",
        "style": "educational",
        "web_search_enabled": False,
    }
    values.update(overrides)
    return VideoGenerationAgentState(**values)


@pytest.mark.asyncio
async def test_validate_settings_enforces_v1_limits(monkeypatch):
    monkeypatch.setattr(validate_module, "dispatch_custom_event", lambda *args, **kwargs: None)

    result = await ValidateSettingsNode().ainvoke(
        make_state(duration_seconds=90, fps=60, aspect_ratio="9:16")
    )

    assert result["duration_seconds"] == 30
    assert result["fps"] == 30
    assert result["width"] == 720
    assert result["height"] == 1280


def test_fallback_storyboard_matches_requested_duration():
    state = make_state(duration_seconds=17)

    scenes = StoryboardNode._fallback_storyboard(state)

    assert 3 <= len(scenes) <= 5
    assert sum(scene.duration_seconds for scene in scenes) == 17
    assert all(scene.duration_seconds >= 2 for scene in scenes)
