import asyncio
import io
import json
import mimetypes
import os
import shutil
import uuid
import yaml
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Sequence, Any

import docker
from docker.errors import DockerException, NotFound, APIError
from fastapi import UploadFile
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import Request

from backend.api.skills.model import (
    AgentSkill,
    SandboxSession,
    SkillExecutionArtifact,
    SkillUpdateRequest,
)
from backend.api.conversation.model import ConversationMessageCreateRequest
from backend.api.conversation.service import conversation_service
from backend.config.settings import _settings
from backend.databases.db import get_utc_now
from backend.exceptions.model import InvalidRequestException, ObjectNotFoundException
from backend.utils.blob_storage import blob_storage_client
from backend.utils.constants import Message

service_logger = logger.bind(service="skill-service")


class SkillService:
    def __init__(self):
        self.skills_root = (
            Path(_settings.process_file.root_download_folder).resolve() / "skills"
        )

    @staticmethod
    def _get_request_logger(request: Request | None = None, user_id: int | None = None):
        return service_logger.bind(
            request_id=getattr(getattr(request, "state", None), "request_id", "-"),
            user_id=user_id
            if user_id is not None
            else getattr(getattr(request, "state", None), "user_id", "-"),
        )

    @staticmethod
    def _normalize_filename(filename: str | None) -> str:
        cleaned_name = Path(filename or "untitled").name.strip()
        if not cleaned_name:
            cleaned_name = "untitled"
        return cleaned_name[:255]

    def _parse_skill_md(self, content: str) -> Dict[str, Any]:
        result = {
            "name": "",
            "description": "",
            "allowed_tools": "",
            "content": content,
        }

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    if isinstance(frontmatter, dict):
                        result["name"] = frontmatter.get("name", "")
                        result["description"] = frontmatter.get("description", "")
                        allowed = frontmatter.get("allowed-tools", "")
                        result["allowed_tools"] = allowed if isinstance(allowed, str) else " ".join(allowed) if isinstance(allowed, list) else ""
                        result["content"] = parts[2].strip()
                except yaml.YAMLError:
                    pass

        return result

    def _get_user_skill(
        self,
        db_session: Session,
        user_id: int,
        skill_id: int,
        request_logger,
    ) -> AgentSkill:
        skill = (
            db_session.query(AgentSkill)
            .filter(AgentSkill.id == skill_id, AgentSkill.user_id == user_id)
            .first()
        )
        if not skill:
            request_logger.warning("Skill not found")
            raise ObjectNotFoundException(message=Message.MESSAGE_FILE_NOT_FOUND)
        return skill

    def list_skills(
        self, request: Request, db_session: Session, user_id: int
    ) -> List[AgentSkill]:
        request_logger = self._get_request_logger(request, user_id)
        skills = (
            db_session.query(AgentSkill)
            .filter(AgentSkill.user_id == user_id)
            .order_by(AgentSkill.created_at.desc())
            .all()
        )
        request_logger.debug("Listed skills successfully, count={}", len(skills))
        return skills

    def get_skill(
        self, request: Request, db_session: Session, user_id: int, skill_id: int
    ) -> AgentSkill:
        request_logger = self._get_request_logger(request, user_id)
        return self._get_user_skill(db_session, user_id, skill_id, request_logger)

    async def upload_skill(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        uploaded_file: UploadFile,
    ) -> AgentSkill:
        request_logger = self._get_request_logger(request, user_id)
        if not uploaded_file:
            raise InvalidRequestException(message="No file provided")

        original_name = self._normalize_filename(uploaded_file.filename)
        extension = Path(original_name).suffix.lower()

        if extension not in [".md", ".zip"]:
            raise InvalidRequestException(message="Only .md and .zip files are supported")

        request_logger.info("Uploading skill, name={}", original_name)

        skills_dir = self.skills_root / str(user_id)
        skills_dir.mkdir(parents=True, exist_ok=True)

        skill_folder_name = f"{uuid.uuid4().hex}"
        skill_folder_path = skills_dir / skill_folder_name

        try:
            content_bytes = await uploaded_file.read()

            if extension == ".zip":
                skill_folder_path.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(io.BytesIO(content_bytes), 'r') as zf:
                    for member in zf.namelist():
                        member_path = (skill_folder_path / member).resolve()
                        if not member_path.is_relative_to(skill_folder_path.resolve()):
                            shutil.rmtree(skill_folder_path, ignore_errors=True)
                            raise InvalidRequestException(
                                message="Zip file contains unsafe path entries"
                            )
                    zf.extractall(path=skill_folder_path)

                md_files = list(skill_folder_path.rglob("*.md"))
                if not md_files:
                    shutil.rmtree(skill_folder_path, ignore_errors=True)
                    raise InvalidRequestException(message="No .md files found in zip")

                skill_md_path = skill_folder_path / "SKILL.md"
                if not skill_md_path.exists():
                    for md_file in md_files:
                        if md_file.name.lower() == "skill.md":
                            skill_md_path = md_file
                            break
                    else:
                        skill_md_path = md_files[0]

                content = skill_md_path.read_text(encoding="utf-8", errors="ignore")
                file_size = sum(f.stat().st_size for f in skill_folder_path.rglob("*") if f.is_file())

            else:
                skill_folder_path.mkdir(parents=True, exist_ok=True)
                skill_md_path = skill_folder_path / "SKILL.md"
                skill_md_path.write_bytes(content_bytes)
                content = content_bytes.decode("utf-8", errors="ignore")
                file_size = len(content_bytes)

            parsed = self._parse_skill_md(content)

            # Upload to Azure Blob Storage for durable download access.
            # Local copy is kept for sandbox Docker volume mounts.
            blob_path: str | None = None
            try:
                blob_key = f"skills/{user_id}/{skill_folder_name}{extension}"
                content_type = (
                    "application/zip" if extension == ".zip" else "text/markdown"
                )
                blob_path = blob_storage_client.upload_bytes(
                    blob_path=blob_key,
                    data=io.BytesIO(content_bytes),
                    content_type=content_type,
                )
                request_logger.info("Uploaded skill to blob: {}", blob_path)
            except Exception as blob_exc:
                request_logger.warning(
                    "Failed to upload skill to blob (skill will be stored locally only): {}",
                    blob_exc,
                )

            now = get_utc_now()

            skill = AgentSkill(
                user_id=user_id,
                name=parsed["name"] or original_name,
                description=parsed["description"],
                storage_path=str(skill_folder_path),
                blob_path=blob_path,
                skill_content=parsed["content"],
                allowed_tools=parsed["allowed_tools"],
                file_type="folder",
                is_active=True,
                is_selected=True,
                size=file_size,
                created_at=now,
                updated_at=now,
            )

            db_session.add(skill)
            db_session.commit()
            db_session.refresh(skill)

            request_logger.info(
                "Skill uploaded successfully, id={} name={} folder={}",
                skill.id,
                skill.name,
                skill_folder_name,
            )
            return skill

        except Exception as e:
            if skill_folder_path.exists():
                shutil.rmtree(skill_folder_path, ignore_errors=True)
            raise e
        finally:
            await uploaded_file.close()

    def update_skill(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        skill_id: int,
        update_request: SkillUpdateRequest,
    ) -> AgentSkill:
        request_logger = self._get_request_logger(request, user_id)
        skill = self._get_user_skill(db_session, user_id, skill_id, request_logger)

        update_data = update_request.model_dump(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = get_utc_now()
            for field, value in update_data.items():
                setattr(skill, field, value)
            db_session.commit()
            db_session.refresh(skill)

        request_logger.info("Updated skill id={}", skill_id)
        return skill

    def delete_skill(
        self, request: Request, db_session: Session, user_id: int, skill_id: int
    ) -> Dict:
        request_logger = self._get_request_logger(request, user_id)
        skill = self._get_user_skill(db_session, user_id, skill_id, request_logger)

        storage_path = Path(str(skill.storage_path))
        blob_path = skill.blob_path
        db_session.delete(skill)
        db_session.commit()

        # Delete from Azure Blob Storage
        if blob_path:
            try:
                blob_storage_client.delete_blob(blob_path)
            except Exception as exc:
                request_logger.warning("Failed to delete skill blob path={}: {}", blob_path, exc)

        if storage_path.exists():
            try:
                if storage_path.is_dir():
                    shutil.rmtree(storage_path)
                else:
                    storage_path.unlink(missing_ok=True)
            except OSError as e:
                request_logger.warning("Unable to remove skill: {}", e)

        request_logger.info("Deleted skill id={}", skill_id)
        return {"message": "Skill deleted successfully"}

    def toggle_skill_selection(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        skill_id: int,
        is_selected: bool,
    ) -> AgentSkill:
        request_logger = self._get_request_logger(request, user_id)
        skill = self._get_user_skill(db_session, user_id, skill_id, request_logger)

        skill.is_selected = is_selected
        skill.updated_at = get_utc_now()
        db_session.commit()
        db_session.refresh(skill)

        request_logger.info(
            "Toggled skill selection id={} is_selected={}", skill_id, is_selected
        )
        return skill

    def load_example_skills(
        self, request: Request, db_session: Session, user_id: int
    ) -> List[AgentSkill]:
        """Import pre-built example skills from test_data/full_skills/."""
        request_logger = self._get_request_logger(request, user_id)
        example_dir = Path(__file__).resolve().parent.parent.parent.parent / "test_data" / "full_skills"

        if not example_dir.exists():
            raise ObjectNotFoundException(message="Example skills directory not found")

        user_skills_dir = self.skills_root / str(user_id)
        user_skills_dir.mkdir(parents=True, exist_ok=True)

        imported: List[AgentSkill] = []
        now = get_utc_now()

        for skill_folder in sorted(example_dir.iterdir()):
            if not skill_folder.is_dir():
                continue
            skill_md = skill_folder / "SKILL.md"
            if not skill_md.exists():
                continue

            content = skill_md.read_text(encoding="utf-8", errors="ignore")
            parsed = self._parse_skill_md(content)
            skill_name = parsed["name"] or skill_folder.name

            existing = (
                db_session.query(AgentSkill)
                .filter(AgentSkill.user_id == user_id, AgentSkill.name == skill_name)
                .first()
            )
            if existing:
                request_logger.debug("Example skill '{}' already exists, skipping", skill_name)
                imported.append(existing)
                continue

            target_folder = user_skills_dir / skill_folder.name
            if target_folder.exists():
                shutil.rmtree(target_folder)
            shutil.copytree(skill_folder, target_folder)

            total_size = sum(
                f.stat().st_size for f in target_folder.rglob("*") if f.is_file()
            )

            skill = AgentSkill(
                user_id=user_id,
                name=skill_name,
                description=parsed["description"],
                storage_path=str(target_folder),
                skill_content=parsed["content"],
                allowed_tools=parsed.get("allowed_tools", ""),
                file_type="folder",
                is_active=True,
                is_selected=False,
                size=total_size,
                created_at=now,
                updated_at=now,
            )
            db_session.add(skill)
            imported.append(skill)
            request_logger.info("Imported example skill: {}", skill_name)

        db_session.commit()
        for skill in imported:
            db_session.refresh(skill)

        request_logger.info("Loaded {} example skill(s)", len(imported))
        return imported


class DockerSandboxManager:
    """Manages Docker containers as sandboxes for skill execution."""

    def __init__(self):
        try:
            self.client = docker.from_env()
            service_logger.info("Docker client initialized successfully")
        except DockerException as e:
            service_logger.error("Failed to initialize Docker client: {}", e)
            self.client = None

    def _get_container_name(self, user_id: int, sandbox_index: int) -> str:
        return f"multiagentx-sandbox-{user_id}-{sandbox_index}"

    def _create_sandbox_container(
        self,
        user_id: int,
        sandbox_index: int,
        skills: Sequence[AgentSkill],
        user_message: str,
    ) -> Optional[docker.models.containers.Container]:
        if not self.client:
            service_logger.error("Docker client not available")
            return None

        container_name = self._get_container_name(user_id, sandbox_index)

        try:
            old_container = self.client.containers.get(container_name)
            old_container.stop(timeout=5)
            old_container.remove(force=True)
            service_logger.info("Removed old sandbox container: {}", container_name)
        except NotFound:
            pass
        except APIError as e:
            service_logger.warning("Error cleaning up old container: {}", e)

        sandbox_dir = Path(_settings.skills.sandbox_base_dir).resolve() / str(user_id) / f"sandbox_{sandbox_index}"
        sandbox_dir.mkdir(parents=True, exist_ok=True)

        primary_skill = skills[0]
        skill_folder_path = Path(primary_skill.storage_path).resolve()

        self._prepare_sandbox_workspace(sandbox_dir, skills, user_message)

        try:
            container = self.client.containers.run(
                image=_settings.skills.sandbox_image or "python:3.11-slim",
                command="tail -f /dev/null",
                detach=True,
                remove=False,
                mem_limit=_settings.skills.sandbox_memory or "2g",
                cpu_quota=int(float(_settings.skills.sandbox_cpu or "1") * 100000),
                network_mode="bridge",
                volumes={
                    str(sandbox_dir): {"bind": "/workspace", "mode": "rw"},
                    str(skill_folder_path): {"bind": "/skill", "mode": "ro"},
                },
                working_dir="/workspace",
                environment={
                    "ANTHROPIC_API_KEY": _settings.skills.azure_anthropic_api_key or _settings.skills.anthropic_api_key or "",
                    "REAL_ANTHROPIC_BASE_URL": _settings.skills.azure_anthropic_base_url or "",
                    "CLAUDE_MODEL": _settings.skills.azure_anthropic_deployment or _settings.skills.default_model or "claude-sonnet-4-5",
                },
                labels={
                    "app": "multiagentx",
                    "type": "sandbox",
                    "user_id": str(user_id),
                    "sandbox_index": str(sandbox_index),
                    "skill_id": str(primary_skill.id),
                },
            )

            service_logger.info(
                "Created sandbox container: {} for {} skill(s)",
                container_name,
                len(skills),
            )
            return container

        except APIError as e:
            service_logger.error("Failed to create sandbox container: {}", e)
            return None
        except Exception as e:
            service_logger.error("Unexpected error creating container: {}", e)
            return None

    def _prepare_sandbox_workspace(
        self,
        sandbox_dir: Path,
        skills: Sequence[AgentSkill],
        user_task: str,
    ) -> None:
        """Set up workspace with Claude CLI configuration and skills."""
        (sandbox_dir / "output").mkdir(parents=True, exist_ok=True)

        # Write user task
        (sandbox_dir / "user_task.txt").write_text(user_task)

        # Create ~/.claude/skills/ directory structure (mounted at /workspace/.claude/skills/)
        claude_skills_dir = sandbox_dir / ".claude" / "skills"
        claude_skills_dir.mkdir(parents=True, exist_ok=True)

        # Copy each skill's SKILL.md into .claude/skills/
        for skill in skills:
            skill_storage = Path(skill.storage_path).resolve()
            skill_md_path = skill_storage / "SKILL.md"
            if skill_md_path.exists():
                safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in skill.name)
                dest = claude_skills_dir / f"{safe_name}.md"
                shutil.copy2(skill_md_path, dest)
            elif skill.skill_content:
                safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in skill.name)
                dest = claude_skills_dir / f"{safe_name}.md"
                dest.write_text(skill.skill_content, encoding="utf-8")

        # Create CLAUDE.md project instructions
        claude_md_content = """# Sandbox Execution Environment

## Directory Layout
- /workspace/ — Working directory (use freely for intermediate work)
- /workspace/output/ — DELIVERABLES ONLY: Save ONLY the final result file(s) here
- /skill/ — Skill folder (read-only, contains SKILL.md and resources)

## Output Rules — CRITICAL
1. `/workspace/output/` is for the **final deliverable only** — do NOT save scripts, intermediate files, thumbnails, logs, or QA images there
2. Save exactly the file(s) the user asked for — if they asked for a .pptx, save only the .pptx
3. All intermediate work (scripts, thumbnails, temp files) must stay in /workspace/, NOT in /workspace/output/
4. Use descriptive filenames (e.g., financial_report_2024.pdf, not file1.pdf)
5. Read /skill/SKILL.md for skill-specific instructions and templates

## Available Packages
- Python: python-pptx, python-docx, openpyxl, pillow, pyyaml, requests, httpx
- Node.js: pptxgenjs (global)
"""
        (sandbox_dir / "CLAUDE.md").write_text(claude_md_content)

        # Create Claude CLI settings (dangerously-skip-permissions is set via CLI flag)
        claude_settings = {
            "permissions": {
                "allow": [
                    "Bash(*)",
                    "Read(*)",
                    "Write(*)",
                    "WebFetch(*)",
                ]
            }
        }
        claude_settings_dir = sandbox_dir / ".claude"
        (claude_settings_dir / "settings.json").write_text(
            json.dumps(claude_settings, indent=2)
        )

        # Create executor shell script that invokes Claude CLI
        model = _settings.skills.azure_anthropic_deployment or _settings.skills.default_model or "claude-sonnet-4-5"
        max_turns = _settings.skills.max_turns or 10

        # Node.js reverse proxy that strips unsupported beta headers for Azure endpoints
        proxy_script = r"""
const http = require('http');
const https = require('https');
const { URL } = require('url');

const UPSTREAM = (process.env.REAL_ANTHROPIC_BASE_URL || 'https://api.anthropic.com').replace(/\/+$/, '');
const STRIP_BETAS = new Set(['advisor-tool-2026-03-01']);

const server = http.createServer((req, res) => {
  // Concatenate paths so /anthropic/v1/messages is preserved (new URL() would drop base path)
  const target = new URL(UPSTREAM + req.url);
  const headers = { ...req.headers };
  delete headers.host;

  if (headers['anthropic-beta']) {
    const betas = headers['anthropic-beta']
      .split(',')
      .map(b => b.trim())
      .filter(b => !STRIP_BETAS.has(b));
    if (betas.length > 0) {
      headers['anthropic-beta'] = betas.join(',');
    } else {
      delete headers['anthropic-beta'];
    }
  }

  const protocol = target.protocol === 'https:' ? https : http;
  const proxyReq = protocol.request(target, {
    method: req.method,
    headers,
  }, (proxyRes) => {
    res.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(res);
  });

  proxyReq.on('error', (e) => {
    res.writeHead(502);
    res.end('Proxy error: ' + e.message);
  });

  req.pipe(proxyReq);
});

server.listen(9999, '127.0.0.1', () => {
  process.stdout.write('PROXY_READY\n');
});
"""
        (sandbox_dir / "beta_proxy.js").write_text(proxy_script)

        script_content = f"""#!/bin/bash
set -euo pipefail

export HOME=/home/sandbox

# Link workspace .claude config to user home so Claude CLI finds it
ln -sfn /workspace/.claude "$HOME/.claude"

# Start beta-header proxy if an Azure/custom base URL is configured
if [ -n "${{REAL_ANTHROPIC_BASE_URL:-}}" ]; then
    node /workspace/beta_proxy.js &
    PROXY_PID=$!
    # Wait for proxy to be ready
    for i in $(seq 1 20); do
        if curl -s http://127.0.0.1:9999/ >/dev/null 2>&1; then break; fi
        sleep 0.1
    done
    export ANTHROPIC_BASE_URL="http://127.0.0.1:9999"
    trap "kill $PROXY_PID 2>/dev/null" EXIT
fi

echo "[SANDBOX] Starting Claude CLI execution..."
echo "=========================================="

USER_TASK=$(cat /workspace/user_task.txt)

# Run Claude CLI with full permissions
exec claude -p "$USER_TASK" \\
    --dangerously-skip-permissions \\
    --output-format stream-json \\
    --verbose \\
    --model "{model}" \\
    --max-turns {max_turns}
"""
        script_path = sandbox_dir / "execute_task.sh"
        script_path.write_text(script_content)
        script_path.chmod(0o755)

    def execute_in_sandbox(
        self,
        container_id: str,
        command: str,
        timeout: int = 300,
    ) -> tuple[int, str, str]:
        if not self.client:
            return 1, "", "Docker client not available"

        try:
            container = self.client.containers.get(container_id)

            result = container.exec_run(
                cmd=["sh", "-c", command],
                stdout=True,
                stderr=True,
                tty=False,
                user="sandbox",
            )

            exit_code = result.exit_code
            output = result.output.decode('utf-8', errors='ignore') if result.output else ""

            return exit_code, output, ""

        except NotFound:
            return 1, "", f"Container {container_id} not found"
        except Exception as e:
            return 1, "", str(e)

    def stream_execute_in_sandbox(
        self,
        container_id: str,
        command: str,
        timeout: int = 300,
    ) -> AsyncGenerator[tuple[str, str], None]:
        if not self.client:
            yield ("error", "Docker client not available")
            return

        try:
            container = self.client.containers.get(container_id)

            exec_result = container.client.api.exec_create(
                container.id,
                ["sh", "-c", command],
                stdout=True,
                stderr=True,
                tty=False,
                user="sandbox",
            )

            exec_id = exec_result['Id']

            stream = container.client.api.exec_start(
                exec_id,
                stream=True,
                demux=True,
            )

            for chunk in stream:
                if chunk:
                    stdout, stderr = chunk
                    if stdout:
                        yield ("stdout", stdout.decode('utf-8', errors='ignore'))
                    if stderr:
                        yield ("stderr", stderr.decode('utf-8', errors='ignore'))

        except NotFound:
            yield ("error", f"Container {container_id} not found")
        except Exception as e:
            yield ("error", str(e))

    def cleanup_sandbox(self, user_id: int, sandbox_index: int) -> bool:
        if not self.client:
            return False

        container_name = self._get_container_name(user_id, sandbox_index)

        try:
            container = self.client.containers.get(container_name)
            container.stop(timeout=5)
            container.remove(force=True)
            service_logger.info("Cleaned up sandbox container: {}", container_name)
            return True
        except NotFound:
            return True
        except Exception as e:
            service_logger.error("Error cleaning up sandbox: {}", e)
            return False

    def get_container_status(self, user_id: int, sandbox_index: int) -> Optional[str]:
        if not self.client:
            return None

        container_name = self._get_container_name(user_id, sandbox_index)

        try:
            container = self.client.containers.get(container_name)
            return container.status
        except NotFound:
            return None
        except Exception:
            return None

    def list_output_files(self, user_id: int, sandbox_index: int) -> List[Dict[str, Any]]:
        if not self.client:
            return []

        container_name = self._get_container_name(user_id, sandbox_index)
        sandbox_dir = Path(_settings.skills.sandbox_base_dir).resolve() / str(user_id) / f"sandbox_{sandbox_index}"
        output_dir = sandbox_dir / "output"

        # Only surface deliverable file types to the user.
        # Intermediate files (scripts, thumbnail images, temp files) are excluded.
        DOCUMENT_EXTENSIONS = {
            ".pptx", ".docx", ".xlsx", ".pdf",
            ".csv", ".json", ".txt", ".md",
            ".zip", ".mp4", ".mp3", ".wav",
        }
        IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
        CODE_EXTENSIONS = {".js", ".ts", ".py", ".sh", ".rb", ".html", ".css"}

        files = []
        if output_dir.exists():
            all_files = [f for f in output_dir.iterdir() if f.is_file()]
            documents = [f for f in all_files if f.suffix.lower() in DOCUMENT_EXTENSIONS]
            images = [f for f in all_files if f.suffix.lower() in IMAGE_EXTENSIONS]
            # Show images only when there are no document-type deliverables (pure image task)
            candidates = documents if documents else images if images else [
                f for f in all_files if f.suffix.lower() not in CODE_EXTENSIONS
            ]
            for f in candidates:
                files.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "created": f.stat().st_mtime,
                })
        return files

    def get_output_file(self, user_id: int, sandbox_index: int, filename: str) -> Optional[Path]:
        sandbox_dir = Path(_settings.skills.sandbox_base_dir).resolve() / str(user_id) / f"sandbox_{sandbox_index}"
        output_dir = (sandbox_dir / "output").resolve()
        file_path = (output_dir / filename).resolve()

        if not file_path.is_relative_to(output_dir):
            return None
        if file_path.exists() and file_path.is_file():
            return file_path
        return None

    def list_user_sandboxes(self, user_id: int) -> List[Dict[str, Any]]:
        if not self.client:
            return []

        try:
            containers = self.client.containers.list(
                filters={
                    "label": f"app=multiagentx,type=sandbox,user_id={user_id}"
                },
                all=True,
            )

            result = []
            for container in containers:
                labels = container.labels or {}
                result.append({
                    "id": container.id,
                    "name": container.name,
                    "status": container.status,
                    "sandbox_index": labels.get("sandbox_index"),
                    "skill_id": labels.get("skill_id"),
                    "created": container.attrs.get("Created"),
                })
            return result
        except Exception as e:
            service_logger.error("Error listing containers: {}", e)
            return []


class SandboxService:
    MAX_SANDBOXES = 10

    def __init__(self):
        self.sandbox_root = (
            Path(_settings.process_file.root_download_folder).resolve() / "sandboxes"
        )
        self.docker_manager = DockerSandboxManager()

    @staticmethod
    def _get_request_logger(request: Request | None = None, user_id: int | None = None):
        return service_logger.bind(
            request_id=getattr(getattr(request, "state", None), "request_id", "-"),
            user_id=user_id
            if user_id is not None
            else getattr(getattr(request, "state", None), "user_id", "-"),
        )

    def initialize_user_sandboxes(
        self, db_session: Session, user_id: int
    ) -> List[SandboxSession]:
        existing = (
            db_session.query(SandboxSession)
            .filter(SandboxSession.user_id == user_id)
            .all()
        )

        if len(existing) >= self.MAX_SANDBOXES:
            for sandbox in existing:
                container_status = self.docker_manager.get_container_status(
                    user_id, sandbox.sandbox_index
                )
                if container_status is None and sandbox.status == "busy":
                    sandbox.status = "ready"
                    sandbox.current_skill_id = None
                    sandbox.progress = 0
                    sandbox.updated_at = get_utc_now()

            db_session.commit()
            return existing

        now = get_utc_now()
        sandboxes = []

        for i in range(self.MAX_SANDBOXES):
            if not any(s.sandbox_index == i for s in existing):
                sandbox = SandboxSession(
                    user_id=user_id,
                    sandbox_index=i,
                    status="ready",
                    progress=0,
                    created_at=now,
                    updated_at=now,
                )
                db_session.add(sandbox)
                sandboxes.append(sandbox)

        if sandboxes:
            db_session.commit()
            for sandbox in sandboxes:
                db_session.refresh(sandbox)

        return existing + sandboxes

    def list_sandboxes(
        self, request: Request, db_session: Session, user_id: int
    ) -> List[SandboxSession]:
        request_logger = self._get_request_logger(request, user_id)
        sandboxes = self.initialize_user_sandboxes(db_session, user_id)

        for sandbox in sandboxes:
            container_status = self.docker_manager.get_container_status(
                user_id, sandbox.sandbox_index
            )

            if container_status is None:
                if sandbox.status == "busy":
                    sandbox.status = "ready"
                    sandbox.current_skill_id = None
                    sandbox.progress = 0
                    sandbox.updated_at = get_utc_now()
            else:
                if container_status == "running":
                    if sandbox.status != "busy":
                        sandbox.status = "busy"
                        sandbox.updated_at = get_utc_now()

        db_session.commit()
        sandboxes.sort(key=lambda s: s.sandbox_index)
        request_logger.debug("Listed sandboxes, count={}", len(sandboxes))
        return sandboxes

    def get_available_sandbox(
        self, db_session: Session, user_id: int
    ) -> Optional[SandboxSession]:
        sandbox = (
            db_session.query(SandboxSession)
            .filter(
                SandboxSession.user_id == user_id,
                SandboxSession.status == "ready",
            )
            .order_by(SandboxSession.sandbox_index)
            .first()
        )

        if sandbox:
            container_status = self.docker_manager.get_container_status(
                user_id, sandbox.sandbox_index
            )
            if container_status == "running":
                self.docker_manager.cleanup_sandbox(user_id, sandbox.sandbox_index)

        return sandbox

    def occupy_sandbox(
        self,
        db_session: Session,
        sandbox_id: int,
        skill_id: int,
        task_description: str,
        user_id: int,
    ) -> SandboxSession:
        sandbox = db_session.query(SandboxSession).filter(
            SandboxSession.id == sandbox_id
        ).first()

        if not sandbox:
            raise ObjectNotFoundException(message="Sandbox not found")

        sandbox.status = "busy"
        sandbox.current_skill_id = skill_id
        sandbox.task_description = task_description
        sandbox.progress = 0
        sandbox.started_at = get_utc_now()
        sandbox.completed_at = None
        sandbox.updated_at = get_utc_now()

        db_session.commit()
        db_session.refresh(sandbox)
        return sandbox

    def release_sandbox(
        self,
        db_session: Session,
        sandbox_id: int,
        user_id: int,
        status: str = "ready",
        progress: int = 100,
    ) -> SandboxSession:
        sandbox = db_session.query(SandboxSession).filter(
            SandboxSession.id == sandbox_id
        ).first()

        if not sandbox:
            raise ObjectNotFoundException(message="Sandbox not found")

        self.docker_manager.cleanup_sandbox(user_id, sandbox.sandbox_index)

        sandbox.status = status
        sandbox.progress = progress
        sandbox.current_skill_id = None
        sandbox.task_description = None
        sandbox.completed_at = get_utc_now()
        sandbox.updated_at = get_utc_now()

        db_session.commit()
        db_session.refresh(sandbox)
        return sandbox

    def update_sandbox_progress(
        self,
        db_session: Session,
        sandbox_id: int,
        progress: int,
        status: Optional[str] = None,
    ) -> SandboxSession:
        sandbox = db_session.query(SandboxSession).filter(
            SandboxSession.id == sandbox_id
        ).first()

        if not sandbox:
            raise ObjectNotFoundException(message="Sandbox not found")

        sandbox.progress = min(100, max(0, progress))
        if status:
            sandbox.status = status
        sandbox.updated_at = get_utc_now()

        db_session.commit()
        db_session.refresh(sandbox)
        return sandbox

    async def execute_skill_stream(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        skill_ids: List[int],
        user_message: str,
        conversation_id: int,
    ) -> AsyncGenerator[str, None]:
        request_logger = self._get_request_logger(request, user_id)

        conversation = conversation_service.get_conversation(
            request,
            db_session,
            user_id,
            conversation_id,
        )
        if conversation.chat_type != "skill":
            raise InvalidRequestException(message=Message.MESSAGE_INVALID_REQUEST)

        conversation_service.add_message(
            request,
            db_session,
            user_id,
            conversation_id,
            ConversationMessageCreateRequest(role="user", content=user_message),
        )

        sandbox = self.get_available_sandbox(db_session, user_id)
        if not sandbox:
            yield self._format_sse_event(
                "error", {"message": "No available sandboxes. Please wait for one to become free."}
            )
            return

        skills = (
            db_session.query(AgentSkill)
            .filter(
                AgentSkill.user_id == user_id,
                AgentSkill.id.in_(skill_ids) if skill_ids else AgentSkill.is_selected == True,
                AgentSkill.is_active == True,
            )
            .all()
        )

        if not skills:
            yield self._format_sse_event(
                "error", {"message": "No skills available. Please upload skills first."}
            )
            return

        skill = skills[0]
        self.occupy_sandbox(
            db_session, sandbox.id, skill.id, user_message, user_id
        )

        try:
            skill_names = ", ".join(s.name for s in skills)
            yield self._format_sse_event(
                "status", {"step": "creating", "message": f"Creating sandbox with skill(s): {skill_names}"}
            )

            container = self.docker_manager._create_sandbox_container(
                user_id, sandbox.sandbox_index, skills, user_message
            )

            if not container:
                yield self._format_sse_event(
                    "error", {"message": "Failed to create Docker sandbox"}
                )
                return

            yield self._format_sse_event(
                "status", {"step": "executing", "message": "Running Claude CLI in sandbox..."}
            )

            self.update_sandbox_progress(db_session, sandbox.id, 25, "busy")

            full_output = []
            generated_files = []
            command = "bash /workspace/execute_task.sh"

            async for stream_type, content in self._async_stream_execute(
                container.id, command
            ):
                if stream_type == "error":
                    yield self._format_sse_event("error", {"message": content})
                    return
                else:
                    # Parse Claude CLI stream-json output
                    for line in content.split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            event = json.loads(line)
                        except (json.JSONDecodeError, ValueError):
                            # Plain text output (non-JSON), pass through
                            full_output.append(line + "\n")
                            yield self._format_sse_event("token", {"delta": line + "\n"})
                            continue

                        event_type = event.get("type", "")

                        if event_type == "assistant" and "message" in event:
                            # message is a dict with content[] array of blocks
                            msg = event["message"]
                            if isinstance(msg, dict):
                                for block in msg.get("content", []):
                                    if not isinstance(block, dict):
                                        continue
                                    if block.get("type") == "thinking":
                                        thinking_text = block.get("thinking", "") or block.get("text", "")
                                        if thinking_text:
                                            brief = (thinking_text[:120].replace("\n", " ") + "...") if len(thinking_text) > 120 else thinking_text.replace("\n", " ")
                                            yield self._format_sse_event("thinking", {"message": brief})
                                    elif block.get("type") == "text":
                                        text = block.get("text", "")
                                        if text:
                                            full_output.append(text)
                                            yield self._format_sse_event("token", {"delta": text})
                            elif isinstance(msg, str) and msg:
                                full_output.append(msg)
                                yield self._format_sse_event("token", {"delta": msg})

                        elif event_type == "tool_use":
                            tool_name = event.get("name", "tool")
                            tool_input = event.get("input", {})
                            if tool_name == "bash":
                                cmd = str(tool_input.get("command", "")).strip()
                                brief = (cmd[:80] + "...") if len(cmd) > 80 else cmd
                                label = f"Running: {brief}"
                            else:
                                label = f"Using tool: {tool_name}"
                            yield self._format_sse_event("tool_use", {"tool": tool_name, "message": label})

                        elif event_type == "content_block_delta":
                            delta = event.get("delta", {})
                            text = delta.get("text", "")
                            if text:
                                full_output.append(text)
                                yield self._format_sse_event("token", {"delta": text})

                        elif event_type == "result":
                            result_text = event.get("result", "")
                            if result_text and not full_output:
                                full_output.append(result_text)
                                yield self._format_sse_event("token", {"delta": result_text})

                        elif event_type == "system":
                            msg = event.get("message", "")
                            if msg:
                                yield self._format_sse_event(
                                    "status", {"step": "system", "message": msg}
                                )

            result = "".join(full_output)

            self.update_sandbox_progress(db_session, sandbox.id, 100, "busy")

            # Get list of generated files
            output_files = self.docker_manager.list_output_files(user_id, sandbox.sandbox_index)
            sandbox_out_dir = (
                Path(_settings.skills.sandbox_base_dir).resolve()
                / str(user_id)
                / f"sandbox_{sandbox.sandbox_index}"
                / "output"
            )

            # Add file information to the response
            file_attachments = []
            for f in output_files:
                blob_url: str | None = None
                try:
                    file_path = sandbox_out_dir / f["name"]
                    if file_path.is_file():
                        blob_key = f"skill-outputs/{user_id}/{sandbox.sandbox_index}/{f['name']}"
                        content_type = mimetypes.guess_type(f["name"])[0] or "application/octet-stream"
                        with open(file_path, "rb") as file_data:
                            blob_storage_client.upload_bytes(
                                blob_path=blob_key,
                                data=file_data,
                                content_type=content_type,
                            )
                        blob_url = blob_storage_client.generate_sas_url(blob_key, expiry_hours=24)
                        request_logger.info("Uploaded sandbox output to blob: {}", blob_key)
                        # Delete from local host filesystem
                        try:
                            file_path.unlink()
                        except Exception as del_exc:
                            request_logger.warning("Failed to delete local output file {}: {}", file_path, del_exc)
                except Exception as blob_exc:
                    request_logger.warning("Failed to upload output file to blob: {}", blob_exc)

                file_info = {
                    "name": f["name"],
                    "size": f["size"],
                    "sandbox_index": sandbox.sandbox_index,
                    "download_url": f"/skills/sandboxes/{sandbox.sandbox_index}/files/{f['name']}",
                    "blob_url": blob_url,
                }
                file_attachments.append(file_info)
                yield self._format_sse_event("file", file_info)

            # Create message content with file references
            message_content = result or "Execution completed without textual output."
            if file_attachments:
                message_content += f"\n\n📎 Generated {len(file_attachments)} file(s):"
                for f in file_attachments:
                    message_content += f"\n- {f['name']} ({f['size']:,} bytes)"

            new_message, _ = conversation_service.add_message(
                request,
                db_session,
                user_id,
                conversation_id,
                ConversationMessageCreateRequest(role="assistant", content=message_content),
            )

            # Persist artifacts to database for permanent access
            for f in file_attachments:
                if f.get("blob_url"):
                    try:
                        blob_key = f"skill-outputs/{user_id}/{sandbox.sandbox_index}/{f['name']}"
                        artifact = SkillExecutionArtifact(
                            user_id=user_id,
                            conversation_id=conversation_id,
                            message_id=new_message.id if new_message else None,
                            skill_id=skill.id if skill else None,
                            sandbox_index=sandbox.sandbox_index,
                            file_name=f["name"],
                            blob_path=blob_key,
                            content_type=mimetypes.guess_type(f["name"])[0] or "application/octet-stream",
                            size=f["size"],
                            created_at=get_utc_now(),
                        )
                        db_session.add(artifact)
                        request_logger.info("Persisted artifact to DB: {} for message_id={}", f["name"], new_message.id if new_message else None)
                    except Exception as artifact_exc:
                        request_logger.warning("Failed to persist artifact to DB: {}", artifact_exc)
            db_session.commit()

            yield self._format_sse_event("done", {"output": result, "files": file_attachments})

        except Exception as e:
            request_logger.error("Error executing skill: {}", e)
            try:
                conversation_service.add_message(
                    request,
                    db_session,
                    user_id,
                    conversation_id,
                    ConversationMessageCreateRequest(role="assistant", content=f"Execution failed: {str(e)}"),
                )
            except Exception:
                request_logger.warning("Failed to persist skill execution error to conversation")
            yield self._format_sse_event("error", {"message": str(e)})
        finally:
            # Clean up entire workspace inside the container (output + input files)
            try:
                container_name = self.docker_manager._get_container_name(user_id, sandbox.sandbox_index)
                container = self.docker_manager.client.containers.get(container_name)
                container.exec_run(
                    cmd=["sh", "-c", "rm -rf /workspace/output/* /workspace/input/* /workspace/user_task.txt"],
                    user="sandbox",
                )
                request_logger.info("Cleaned up sandbox workspace for user={} sandbox={}", user_id, sandbox.sandbox_index)
            except Exception as cleanup_exc:
                request_logger.warning("Failed to clean up sandbox workspace: {}", cleanup_exc)
            # Clean up host-side sandbox directory
            try:
                sandbox_host_dir = (
                    Path(_settings.skills.sandbox_base_dir).resolve()
                    / str(user_id)
                    / f"sandbox_{sandbox.sandbox_index}"
                )
                for sub in ("output", "input"):
                    sub_dir = sandbox_host_dir / sub
                    if sub_dir.exists():
                        shutil.rmtree(sub_dir, ignore_errors=True)
                        sub_dir.mkdir(parents=True, exist_ok=True)
                user_task_file = sandbox_host_dir / "user_task.txt"
                user_task_file.unlink(missing_ok=True)
            except Exception as host_cleanup_exc:
                request_logger.warning("Failed to clean up host sandbox dir: {}", host_cleanup_exc)
            self.release_sandbox(db_session, sandbox.id, user_id, "ready", 100)

    async def _async_stream_execute(
        self,
        container_id: str,
        command: str,
        timeout: int = 300,
    ) -> AsyncGenerator[tuple[str, str], None]:
        from concurrent.futures import ThreadPoolExecutor
        
        loop = asyncio.get_event_loop()
        queue = asyncio.Queue()
        
        def stream_in_thread():
            try:
                for stream_type, content in self.docker_manager.stream_execute_in_sandbox(
                    container_id, command, timeout
                ):
                    asyncio.run_coroutine_threadsafe(
                        queue.put((stream_type, content)), 
                        loop
                    )
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)
            except Exception as e:
                asyncio.run_coroutine_threadsafe(
                    queue.put(("error", str(e))), 
                    loop
                )
                asyncio.run_coroutine_threadsafe(queue.put(None), loop)
        
        executor = ThreadPoolExecutor(max_workers=1)
        executor.submit(stream_in_thread)
        
        try:
            while True:
                chunk = await asyncio.wait_for(queue.get(), timeout=timeout)
                if chunk is None:
                    break
                yield chunk
        except asyncio.TimeoutError:
            yield ("error", f"Execution timed out after {timeout} seconds")
        finally:
            executor.shutdown(wait=False)

    @staticmethod
    def _format_sse_event(event: str, data: Dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


skill_service = SkillService()
sandbox_service = SandboxService()