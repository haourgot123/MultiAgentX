import asyncio
import json
from pathlib import Path

from langchain_core.callbacks import adispatch_custom_event
from langchain_core.runnables import Runnable
from loguru import logger

from backend.agents.video_generation_agent.state import VideoGenerationAgentState
from backend.config.settings import _settings



class RenderNode(Runnable):
    def invoke(self, state: VideoGenerationAgentState, **kwargs):
        pass

    @staticmethod
    def _repo_root() -> Path:
        return Path(__file__).resolve().parents[4]

    async def ainvoke(self, state: VideoGenerationAgentState, **kwargs):
        await adispatch_custom_event(
            "status",
            {
                "step": "rendering",
                "message": "Rendering video with Remotion...",
            },
        )

        repo_root = self._repo_root()
        renderer_dir = repo_root / _settings.video_generation.renderer_project_dir
        if not renderer_dir.exists():
            raise RuntimeError(f"Remotion renderer directory not found: {renderer_dir}")

        workdir = repo_root / _settings.video_generation.render_workdir / str(state.job_id)
        workdir.mkdir(parents=True, exist_ok=True)
        source_dir = renderer_dir / ".generated" / str(state.job_id)
        source_dir.mkdir(parents=True, exist_ok=True)

        input_path = workdir / "input.json"
        output_path = workdir / "video.mp4"
        thumbnail_path = workdir / "thumbnail.png"
        entry_path = source_dir / "index.tsx"
        input_path.write_text(
            json.dumps(state.remotion_input, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if not state.composition_code.strip():
            raise RuntimeError("No Remotion composition code was generated")
        entry_path.write_text(state.composition_code, encoding="utf-8")

        command = [
            "npm",
            "run",
            "render",
            "--",
            "--entry",
            str(entry_path),
            "--composition-id",
            state.composition_id,
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--thumbnail",
            str(thumbnail_path),
        ]
        logger.info(f"[VideoGenerationAgent (RenderNode)] Running Remotion command in {renderer_dir}: {command}")
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(renderer_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=_settings.video_generation.render_timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise RuntimeError("Remotion render timed out") from exc

        if stdout:
            logger.debug(f"[VideoGenerationAgent (RenderNode)] Remotion stdout: {stdout.decode(errors='ignore')[-2000:]}")
        if stderr:
            logger.debug(f"[VideoGenerationAgent (RenderNode)] Remotion stderr: {stderr.decode(errors='ignore')[-2000:]}")

        if process.returncode != 0:
            error_text = stderr.decode(errors="ignore").strip() or "Remotion render failed"
            raise RuntimeError(error_text[-1000:])

        if not output_path.exists():
            raise RuntimeError("Remotion render completed without an output video")

        await adispatch_custom_event(
            "status",
            {
                "step": "rendering",
                "message": "Render complete. Uploading video...",
            },
        )

        return {
            "workdir": workdir,
            "video_path": output_path,
            "thumbnail_path": thumbnail_path if thumbnail_path.exists() else None,
        }
