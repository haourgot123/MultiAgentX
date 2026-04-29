import asyncio
import io
import json
import mimetypes
import os
import shutil
import uuid
import yaml
import zipfile
from collections import deque
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any, AsyncGenerator, Dict, List, Optional, Sequence

import docker
from docker.errors import DockerException, NotFound, APIError
from fastapi import UploadFile
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import Request

from backend.api.skills.model import (
    AgentSkill,
    SandboxSocketEvent,
    SkillUpdateRequest,
)
from backend.api.conversation.model import ConversationMessageCreateRequest
from backend.api.conversation.service import conversation_service
from backend.config.settings import _settings
from backend.databases.db import get_utc_now
from backend.exceptions.model import InvalidRequestException, ObjectNotFoundException
from backend.realtime.socketio import socketio_manager
from backend.utils.blob_storage import blob_storage_client
from backend.utils.constants import Message
from backend.utils.retention import mark_for_retention_delete



class SkillService:
    def __init__(self):
        self.skills_root = (
            Path(_settings.process_file.root_download_folder).resolve() / "skills"
        )

    @staticmethod
    def _get_log_prefix(request: Request | None = None, user_id: int | None = None) -> str:
        request_id = getattr(getattr(request, "state", None), "request_id", "-")
        resolved_user_id = (
            user_id
            if user_id is not None
            else getattr(getattr(request, "state", None), "user_id", "-")
        )
        return f"[SkillService][request_id={request_id}][user_id={resolved_user_id}]"

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
        log_prefix: str,
    ) -> AgentSkill:
        skill = (
            db_session.query(AgentSkill)
            .filter(
                AgentSkill.id == skill_id,
                AgentSkill.user_id == user_id,
                AgentSkill.deleted_at.is_(None),
            )
            .first()
        )
        if not skill:
            logger.warning(f"{log_prefix} Skill not found")
            raise ObjectNotFoundException(message=Message.MESSAGE_FILE_NOT_FOUND)
        return skill

    def list_skills(
        self, request: Request, db_session: Session, user_id: int
    ) -> List[AgentSkill]:
        log_prefix = self._get_log_prefix(request, user_id)
        skills = (
            db_session.query(AgentSkill)
            .filter(
                AgentSkill.user_id == user_id,
                AgentSkill.deleted_at.is_(None),
            )
            .order_by(AgentSkill.created_at.desc())
            .all()
        )
        logger.debug(f"{log_prefix} Listed skills successfully, count={len(skills)}")
        return skills

    def get_skill(
        self, request: Request, db_session: Session, user_id: int, skill_id: int
    ) -> AgentSkill:
        log_prefix = self._get_log_prefix(request, user_id)
        return self._get_user_skill(db_session, user_id, skill_id, log_prefix)

    async def upload_skill(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        uploaded_file: UploadFile,
    ) -> AgentSkill:
        log_prefix = self._get_log_prefix(request, user_id)
        if not uploaded_file:
            raise InvalidRequestException(message="No file provided")

        original_name = self._normalize_filename(uploaded_file.filename)
        extension = Path(original_name).suffix.lower()

        if extension not in [".md", ".zip"]:
            raise InvalidRequestException(message="Only .md and .zip files are supported")

        logger.info(f"{log_prefix} Uploading skill, name={original_name}")

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
                logger.info(f"{log_prefix} Uploaded skill to blob: {blob_path}")
            except Exception as blob_exc:
                logger.warning(
                    f"{log_prefix} Failed to upload skill to blob "
                    f"(skill will be stored locally only): {blob_exc}"
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

            logger.info(
                f"{log_prefix} Skill uploaded successfully, id={skill.id} "
                f"name={skill.name} folder={skill_folder_name}"
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
        log_prefix = self._get_log_prefix(request, user_id)
        skill = self._get_user_skill(db_session, user_id, skill_id, log_prefix)

        update_data = update_request.model_dump(exclude_unset=True)
        if update_data:
            update_data["updated_at"] = get_utc_now()
            for field, value in update_data.items():
                setattr(skill, field, value)
            db_session.commit()
            db_session.refresh(skill)

        logger.info(f"{log_prefix} Updated skill id={skill_id}")
        return skill

    def delete_skill(
        self, request: Request, db_session: Session, user_id: int, skill_id: int
    ) -> Dict:
        log_prefix = self._get_log_prefix(request, user_id)
        skill = self._get_user_skill(db_session, user_id, skill_id, log_prefix)

        mark_for_retention_delete(skill)
        skill.is_active = False
        skill.is_selected = False
        db_session.commit()

        logger.info(f"{log_prefix} Soft deleted skill id={skill_id} purge_after={skill.purge_after}")
        return {"message": "Skill deleted successfully"}

    def toggle_skill_selection(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        skill_id: int,
        is_selected: bool,
    ) -> AgentSkill:
        log_prefix = self._get_log_prefix(request, user_id)
        skill = self._get_user_skill(db_session, user_id, skill_id, log_prefix)

        skill.is_selected = is_selected
        skill.updated_at = get_utc_now()
        db_session.commit()
        db_session.refresh(skill)

        logger.info(f"{log_prefix} Toggled skill selection id={skill_id} is_selected={is_selected}")
        return skill

    def load_example_skills(
        self, request: Request, db_session: Session, user_id: int
    ) -> List[AgentSkill]:
        """Import pre-built example skills from test_data/full_skills/."""
        log_prefix = self._get_log_prefix(request, user_id)
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
                .filter(
                    AgentSkill.user_id == user_id,
                    AgentSkill.name == skill_name,
                    AgentSkill.deleted_at.is_(None),
                )
                .first()
            )
            if existing:
                logger.debug(f"{log_prefix} Example skill '{skill_name}' already exists, skipping")
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
            logger.info(f"{log_prefix} Imported example skill: {skill_name}")

        db_session.commit()
        for skill in imported:
            db_session.refresh(skill)

        logger.info(f"{log_prefix} Loaded {len(imported)} example skill(s)")
        return imported


class DockerSandboxManager:
    """Manages Docker containers as sandboxes for skill execution."""

    RESULT_DIR_NAME = "result"

    def __init__(self):
        try:
            self.client = docker.from_env()
            logger.info("[DockerSandboxManager] Docker client initialized successfully")
        except DockerException as e:
            logger.error(f"[DockerSandboxManager] Failed to initialize Docker client: {e}")
            self.client = None

    @staticmethod
    def _get_container_name(sandbox_index: int) -> str:
        return f"multiagentx-sandbox-{sandbox_index}"

    @staticmethod
    def _get_sandbox_dir(sandbox_index: int) -> Path:
        return (
            Path(_settings.skills.sandbox_base_dir).resolve()
            / "pool"
            / f"sandbox_{sandbox_index}"
        )

    def _get_result_dir(self, sandbox_index: int) -> Path:
        return self._get_sandbox_dir(sandbox_index) / self.RESULT_DIR_NAME

    def _create_sandbox_container(
        self,
        sandbox_index: int,
        skills: Sequence[AgentSkill],
    ) -> Optional[docker.models.containers.Container]:
        if not self.client:
            logger.error("[DockerSandboxManager] Docker client not available")
            return None

        container_name = self._get_container_name(sandbox_index)
        sandbox_dir = self._get_sandbox_dir(sandbox_index)
        sandbox_dir.mkdir(parents=True, exist_ok=True)

        primary_skill = skills[0]
        skill_folder_path = Path(primary_skill.storage_path).resolve()

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
                    "sandbox_index": str(sandbox_index),
                    "skill_id": str(primary_skill.id),
                },
                name=container_name,
            )

            logger.info(
                f"[DockerSandboxManager] Created sandbox container: {container_name} "
                f"for {len(skills)} skill(s)"
            )
            return container

        except APIError as e:
            logger.error(f"[DockerSandboxManager] Failed to create sandbox container: {e}")
            return None
        except Exception as e:
            logger.error(f"[DockerSandboxManager] Unexpected error creating container: {e}")
            return None

    def _get_container(
        self, sandbox_index: int
    ) -> Optional[docker.models.containers.Container]:
        if not self.client:
            return None
        try:
            return self.client.containers.get(self._get_container_name(sandbox_index))
        except NotFound:
            return None
        except Exception as exc:
            logger.warning(f"[DockerSandboxManager] Unable to inspect sandbox container index={sandbox_index}: {exc}")
            return None

    def _probe_container(self, container: docker.models.containers.Container) -> bool:
        try:
            result = container.exec_run(
                cmd=[
                    "sh",
                    "-c",
                    f"test -d /workspace && test -d /workspace/{self.RESULT_DIR_NAME} && whoami",
                ],
                stdout=True,
                stderr=True,
                tty=False,
                user="sandbox",
            )
            return result.exit_code == 0
        except Exception as exc:
            logger.warning(f"[DockerSandboxManager] Sandbox health probe failed: {exc}")
            return False

    def _ensure_container_running(
        self,
        sandbox_index: int,
        skills: Sequence[AgentSkill],
    ) -> Optional[docker.models.containers.Container]:
        if not self.client:
            logger.error("[DockerSandboxManager] Docker client not available")
            return None

        container = self._get_container(sandbox_index)
        if container:
            try:
                container.reload()
                if container.status != "running":
                    container.start()
                    container.reload()
                if self._probe_container(container):
                    return container
                self.cleanup_sandbox(sandbox_index)
            except Exception as exc:
                logger.warning(
                    "[DockerSandboxManager] Existing sandbox container was not reusable index={}: {}",
                    sandbox_index,
                    exc,
                )
                self.cleanup_sandbox(sandbox_index)

        return self._create_sandbox_container(sandbox_index, skills)

    def reset_workspace(self, sandbox_index: int) -> Path:
        sandbox_dir = self._get_sandbox_dir(sandbox_index)
        sandbox_dir.mkdir(parents=True, exist_ok=True)

        for child_name in (
            self.RESULT_DIR_NAME,
            "output",
            "input",
            ".claude",
            "user_task.txt",
            "task_prompt.txt",
            "CLAUDE.md",
            "execute_task.sh",
            "beta_proxy.js",
        ):
            target = sandbox_dir / child_name
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            else:
                target.unlink(missing_ok=True)

        return sandbox_dir

    def prepare_workspace(
        self,
        sandbox_index: int,
        skills: Sequence[AgentSkill],
        user_task: str,
    ) -> Path:
        sandbox_dir = self.reset_workspace(sandbox_index)
        self._prepare_sandbox_workspace(sandbox_dir, skills, user_task)
        return sandbox_dir

    def ensure_sandbox_container(
        self,
        sandbox_index: int,
        skills: Sequence[AgentSkill],
        user_task: str,
    ) -> Optional[docker.models.containers.Container]:
        self.prepare_workspace(sandbox_index, skills, user_task)
        return self._ensure_container_running(sandbox_index, skills)

    def _prepare_sandbox_workspace(
        self,
        sandbox_dir: Path,
        skills: Sequence[AgentSkill],
        user_task: str,
    ) -> None:
        """Set up workspace with Claude CLI configuration and skills."""
        result_dir = sandbox_dir / self.RESULT_DIR_NAME
        result_dir.mkdir(parents=True, exist_ok=True)

        # Write user task
        (sandbox_dir / "user_task.txt").write_text(user_task)
        task_prompt = f"""User task:
{user_task}

Execution contract:
- Do all intermediate work in /workspace or subdirectories outside /workspace/{self.RESULT_DIR_NAME}.
- Save only final user-requested deliverable file(s) in /workspace/{self.RESULT_DIR_NAME}.
- Do not put package files, source files, logs, README files, temporary files, screenshots, thumbnails, or analysis notes in /workspace/{self.RESULT_DIR_NAME}.
- If the requested result is a PowerPoint file, the final .pptx must be placed directly in /workspace/{self.RESULT_DIR_NAME}.
- Treat /workspace/{self.RESULT_DIR_NAME} as the only handoff directory. Files outside it will not be returned to the user.
- Final response must use the same language as the user's task.
- Final response should summarize what was completed in Markdown. Do not include raw JSON, tool logs, file paths, or implementation details.
"""
        (sandbox_dir / "task_prompt.txt").write_text(task_prompt)

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
- /workspace/result/ — HANDOFF DIRECTORY: Save ONLY the final user-requested deliverable file(s) here
- /skill/ — Skill folder (read-only, contains SKILL.md and resources)

## Output Rules — CRITICAL
1. `/workspace/result/` is the only handoff directory for returned files
2. Save exactly the file(s) the user asked for there — if they asked for a .pptx, save only the final .pptx
3. All intermediate work (scripts, packages, thumbnails, temp files, logs, QA images) must stay outside /workspace/result/
4. Use descriptive filenames (e.g., financial_report_2024.pdf, not file1.pdf)
5. If /skill/SKILL.md mentions another output folder, still copy the final requested deliverable into /workspace/result/ before finishing
6. Read /skill/SKILL.md for skill-specific instructions and templates

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

server.on('error', (e) => {
  if (e.code === 'EADDRINUSE') {
    process.exit(0);
  }
  throw e;
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
PROXY_PID=""
if [ -n "${{REAL_ANTHROPIC_BASE_URL:-}}" ]; then
    if ! node -e "const net=require('net'); const s=net.connect(9999,'127.0.0.1'); s.on('connect',()=>process.exit(0)); s.on('error',()=>process.exit(1)); setTimeout(()=>process.exit(1),500);" >/dev/null 2>&1; then
        node /workspace/beta_proxy.js >/tmp/multiagentx_beta_proxy.log 2>&1 &
        PROXY_PID=$!
        for i in $(seq 1 20); do
            if node -e "const net=require('net'); const s=net.connect(9999,'127.0.0.1'); s.on('connect',()=>process.exit(0)); s.on('error',()=>process.exit(1)); setTimeout(()=>process.exit(1),500);" >/dev/null 2>&1; then break; fi
            sleep 0.1
        done
    fi
    export ANTHROPIC_BASE_URL="http://127.0.0.1:9999"
fi

echo "[SANDBOX] Starting Claude CLI execution..."
echo "=========================================="

USER_TASK=$(cat /workspace/task_prompt.txt)

# Run Claude CLI with full permissions
set +e
claude -p "$USER_TASK" \\
    --dangerously-skip-permissions \\
    --output-format stream-json \\
    --verbose \\
    --model "{model}" \\
    --max-turns {max_turns}
EXIT_CODE=$?
if [ -n "$PROXY_PID" ]; then
    kill "$PROXY_PID" 2>/dev/null || true
fi
exit "$EXIT_CODE"
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

    def cleanup_sandbox(self, sandbox_index: int) -> bool:
        if not self.client:
            return False

        container_name = self._get_container_name(sandbox_index)

        try:
            container = self.client.containers.get(container_name)
            container.stop(timeout=5)
            container.remove(force=True)
            logger.info(f"[DockerSandboxManager] Cleaned up sandbox container: {container_name}")
            return True
        except NotFound:
            return True
        except Exception as e:
            logger.error(f"[DockerSandboxManager] Error cleaning up sandbox: {e}")
            return False

    def get_container_status(self, sandbox_index: int) -> Optional[str]:
        if not self.client:
            return None

        container_name = self._get_container_name(sandbox_index)

        try:
            container = self.client.containers.get(container_name)
            return container.status
        except NotFound:
            return None
        except Exception:
            return None

    def list_output_files(self, sandbox_index: int) -> List[Dict[str, Any]]:
        result_dir = self._get_result_dir(sandbox_index)

        files = []
        if result_dir.exists():
            for f in result_dir.iterdir():
                if not f.is_file():
                    continue
                files.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "created": f.stat().st_mtime,
                })
        return files

    def collect_output_files(self, sandbox_index: int) -> List[Dict[str, Any]]:
        return self.list_output_files(sandbox_index)

    def get_output_file(self, sandbox_index: int, filename: str) -> Optional[Path]:
        result_dir = self._get_result_dir(sandbox_index).resolve()
        file_path = (result_dir / filename).resolve()

        if not file_path.is_relative_to(result_dir):
            return None
        if file_path.exists() and file_path.is_file():
            return file_path
        return None

    def list_global_sandboxes(self) -> List[Dict[str, Any]]:
        if not self.client:
            return []

        try:
            containers = self.client.containers.list(
                filters={
                    "label": "app=multiagentx,type=sandbox"
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
            logger.error(f"[DockerSandboxManager] Error listing containers: {e}")
            return []


@dataclass
class SandboxSlot:
    id: int
    user_id: Optional[int]
    sandbox_index: int
    status: str
    current_skill_id: Optional[int]
    task_description: Optional[str]
    progress: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class SandboxService:
    def __init__(self):
        self.docker_manager = DockerSandboxManager()
        self.pool_size = max(1, _settings.skills.global_pool_size)
        self.queue_timeout_seconds = max(
            1, _settings.skills.global_queue_timeout_seconds
        )
        self.idle_ttl_seconds = max(60, _settings.skills.global_idle_ttl_seconds)
        self._queue_condition = asyncio.Condition()
        self._wait_queue: deque[str] = deque()
        now = get_utc_now()
        self._sandboxes: dict[int, SandboxSlot] = {
            index: SandboxSlot(
                id=index + 1,
                user_id=None,
                sandbox_index=index,
                status="ready",
                current_skill_id=None,
                task_description=None,
                progress=0,
                started_at=None,
                completed_at=None,
                created_at=now,
                updated_at=now,
            )
            for index in range(self.pool_size)
        }

    @staticmethod
    def _get_log_prefix(request: Request | None = None, user_id: int | None = None) -> str:
        request_id = getattr(getattr(request, "state", None), "request_id", "-")
        resolved_user_id = (
            user_id
            if user_id is not None
            else getattr(getattr(request, "state", None), "user_id", "-")
        )
        return f"[SandboxService][request_id={request_id}][user_id={resolved_user_id}]"

    @staticmethod
    def _coerce_utc_datetime(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @staticmethod
    def _is_public_owner(viewer_user_id: int, sandbox: SandboxSlot) -> bool:
        return sandbox.user_id == viewer_user_id and sandbox.status == "busy"

    @staticmethod
    def _build_public_socket_payload(sandbox: SandboxSlot) -> SandboxSocketEvent:
        return SandboxSocketEvent(
            id=sandbox.id,
            user_id=None,
            sandbox_index=sandbox.sandbox_index,
            status=sandbox.status,
            current_skill_id=None,
            task_description=None,
            progress=sandbox.progress,
            started_at=sandbox.started_at,
            completed_at=sandbox.completed_at,
            updated_at=sandbox.updated_at or get_utc_now(),
        )

    def _emit_sandbox_status(self, sandbox: SandboxSlot) -> None:
        socketio_manager.emit_global_sandbox_status_sync(
            payload=self._build_public_socket_payload(sandbox).model_dump(mode="json")
        )

    def _notify_waiters(self) -> None:
        async def _notify() -> None:
            async with self._queue_condition:
                self._queue_condition.notify_all()

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        loop.create_task(_notify())

    def initialize_global_sandboxes(self, db_session: Session | None = None) -> List[SandboxSlot]:
        now = get_utc_now()
        for index in range(self.pool_size):
            if index not in self._sandboxes:
                self._sandboxes[index] = SandboxSlot(
                    id=index + 1,
                    user_id=None,
                    sandbox_index=index,
                    status="ready",
                    current_skill_id=None,
                    task_description=None,
                    progress=0,
                    started_at=None,
                    completed_at=None,
                    created_at=now,
                    updated_at=now,
                )

        for index in list(self._sandboxes):
            if index >= self.pool_size:
                self._sandboxes.pop(index, None)

        return [self._sandboxes[index] for index in sorted(self._sandboxes)]

    def _mark_sandbox_ready(
        self,
        db_session: Session | None,
        sandbox: SandboxSlot,
        *,
        progress: int = 0,
    ) -> SandboxSlot:
        sandbox.user_id = None
        sandbox.status = "ready"
        sandbox.progress = progress
        sandbox.current_skill_id = None
        sandbox.task_description = None
        sandbox.started_at = None
        sandbox.completed_at = get_utc_now()
        sandbox.updated_at = get_utc_now()
        self._emit_sandbox_status(sandbox)
        self._notify_waiters()
        return sandbox

    def _reap_idle_sandboxes(self, db_session: Session | None = None) -> None:
        now = get_utc_now()
        for sandbox in self.initialize_global_sandboxes(db_session):
            if sandbox.status != "ready":
                continue
            updated_at = self._coerce_utc_datetime(sandbox.updated_at)
            if updated_at is None:
                continue
            age = (now - updated_at).total_seconds()
            if age < self.idle_ttl_seconds:
                continue
            if self.docker_manager.get_container_status(sandbox.sandbox_index):
                self.docker_manager.cleanup_sandbox(sandbox.sandbox_index)

    def _synchronize_sandbox_states(self, db_session: Session | None = None) -> List[SandboxSlot]:
        sandboxes = self.initialize_global_sandboxes(db_session)

        for sandbox in sandboxes:
            container_status = self.docker_manager.get_container_status(
                sandbox.sandbox_index
            )

            if sandbox.status == "busy" and container_status != "running":
                sandbox.user_id = None
                sandbox.status = "ready"
                sandbox.progress = 0
                sandbox.current_skill_id = None
                sandbox.task_description = None
                sandbox.started_at = None
                sandbox.completed_at = get_utc_now()
                sandbox.updated_at = get_utc_now()
            elif sandbox.status == "ready" and container_status == "running":
                continue

        self._reap_idle_sandboxes(db_session)
        return sandboxes

    def list_sandboxes(
        self, request: Request, db_session: Session, user_id: int
    ) -> List[SandboxSlot]:
        log_prefix = self._get_log_prefix(request, user_id)
        sandboxes = self._synchronize_sandbox_states(db_session)
        logger.debug(f"{log_prefix} Listed global sandboxes, count={len(sandboxes)}")
        return sandboxes

    def _claim_ready_sandbox(
        self,
        db_session: Session,
        user_id: int,
        skill_id: int,
        task_description: str,
    ) -> Optional[SandboxSlot]:
        sandboxes = self.initialize_global_sandboxes(db_session)
        sandbox = next((slot for slot in sandboxes if slot.status == "ready"), None)
        if not sandbox:
            return None

        now = get_utc_now()
        sandbox.user_id = user_id
        sandbox.status = "busy"
        sandbox.current_skill_id = skill_id
        sandbox.task_description = task_description
        sandbox.progress = 0
        sandbox.started_at = now
        sandbox.completed_at = None
        sandbox.updated_at = now
        self._emit_sandbox_status(sandbox)
        return sandbox

    async def acquire_sandbox(
        self,
        db_session: Session,
        user_id: int,
        skill_id: int,
        task_description: str,
    ) -> Optional[SandboxSlot]:
        token = uuid.uuid4().hex
        deadline = monotonic() + self.queue_timeout_seconds

        async with self._queue_condition:
            self._wait_queue.append(token)
            while True:
                if self._wait_queue and self._wait_queue[0] == token:
                    self._synchronize_sandbox_states(db_session)
                    sandbox = self._claim_ready_sandbox(
                        db_session,
                        user_id,
                        skill_id,
                        task_description,
                    )
                    if sandbox:
                        self._wait_queue.popleft()
                        self._queue_condition.notify_all()
                        return sandbox

                remaining = deadline - monotonic()
                if remaining <= 0:
                    with suppress(ValueError):
                        self._wait_queue.remove(token)
                    self._queue_condition.notify_all()
                    return None

                try:
                    await asyncio.wait_for(
                        self._queue_condition.wait(),
                        timeout=remaining,
                    )
                except asyncio.TimeoutError:
                    with suppress(ValueError):
                        self._wait_queue.remove(token)
                    self._queue_condition.notify_all()
                    return None

    def release_sandbox(
        self,
        db_session: Session | None,
        sandbox_id: int,
        *,
        destroy_container: bool = False,
        progress: int = 100,
    ) -> SandboxSlot:
        sandbox = next(
            (slot for slot in self.initialize_global_sandboxes(db_session) if slot.id == sandbox_id),
            None,
        )

        if not sandbox:
            raise ObjectNotFoundException(message="Sandbox not found")

        if destroy_container:
            self.docker_manager.cleanup_sandbox(sandbox.sandbox_index)

        return self._mark_sandbox_ready(db_session, sandbox, progress=progress)

    def update_sandbox_progress(
        self,
        db_session: Session | None,
        sandbox_id: int,
        progress: int,
        status: Optional[str] = None,
    ) -> SandboxSlot:
        sandbox = next(
            (slot for slot in self.initialize_global_sandboxes(db_session) if slot.id == sandbox_id),
            None,
        )

        if not sandbox:
            raise ObjectNotFoundException(message="Sandbox not found")

        sandbox.progress = min(100, max(0, progress))
        if status:
            sandbox.status = status
        sandbox.updated_at = get_utc_now()

        self._emit_sandbox_status(sandbox)
        return sandbox

    def _get_sandbox_for_output_access(
        self,
        db_session: Session,
        user_id: int,
        sandbox_index: int,
    ) -> SandboxSlot:
        sandbox = self._sandboxes.get(sandbox_index)
        if not sandbox:
            raise ObjectNotFoundException(message="Sandbox not found")
        if sandbox.user_id != user_id:
            raise ObjectNotFoundException(message="Sandbox output not available")
        return sandbox

    def list_sandbox_files(
        self,
        db_session: Session,
        user_id: int,
        sandbox_index: int,
    ) -> List[Dict[str, Any]]:
        self._get_sandbox_for_output_access(db_session, user_id, sandbox_index)
        return self.docker_manager.list_output_files(sandbox_index)

    def get_sandbox_output_file(
        self,
        db_session: Session,
        user_id: int,
        sandbox_index: int,
        filename: str,
    ) -> Optional[Path]:
        self._get_sandbox_for_output_access(db_session, user_id, sandbox_index)
        return self.docker_manager.get_output_file(sandbox_index, filename)

    async def execute_skill_stream(
        self,
        request: Request,
        db_session: Session,
        user_id: int,
        skill_ids: List[int],
        user_message: str,
        conversation_id: int,
    ) -> AsyncGenerator[str, None]:
        log_prefix = self._get_log_prefix(request, user_id)

        if not _settings.skills.enable_sandbox:
            yield self._format_sse_event(
                "error",
                {"message": "Sandbox execution is disabled by server configuration."},
            )
            return

        conversation = conversation_service.get_conversation(
            request,
            db_session,
            user_id,
            conversation_id,
        )
        if conversation.chat_type != "skill":
            raise InvalidRequestException(message=Message.MESSAGE_INVALID_REQUEST)

        skills = (
            db_session.query(AgentSkill)
            .filter(
                AgentSkill.user_id == user_id,
                AgentSkill.id.in_(skill_ids) if skill_ids else AgentSkill.is_selected == True,
                AgentSkill.is_active == True,
                AgentSkill.deleted_at.is_(None),
            )
            .all()
        )

        if not skills:
            yield self._format_sse_event(
                "error", {"message": "No skills available. Please upload skills first."}
            )
            return

        conversation_service.add_message(
            request,
            db_session,
            user_id,
            conversation_id,
            ConversationMessageCreateRequest(role="user", content=user_message),
        )

        skill = skills[0]
        sandbox = await self.acquire_sandbox(
            db_session,
            user_id,
            skill.id,
            user_message,
        )
        if not sandbox:
            yield self._format_sse_event(
                "error",
                {"message": "All sandboxes are busy. Please retry shortly."},
            )
            return

        destroy_container = False

        try:
            skill_names = ", ".join(s.name for s in skills)
            yield self._format_sse_event(
                "status",
                {
                    "step": "creating",
                    "message": f"Preparing sandbox with skill(s): {skill_names}",
                },
            )

            container = self.docker_manager.ensure_sandbox_container(
                sandbox.sandbox_index,
                skills,
                user_message,
            )
            if not container:
                destroy_container = True
                yield self._format_sse_event(
                    "error", {"message": "Failed to provision Docker sandbox"}
                )
                return

            yield self._format_sse_event(
                "status",
                {"step": "executing", "message": "Running Claude CLI in sandbox..."},
            )

            self.update_sandbox_progress(db_session, sandbox.id, 25, "busy")

            full_output: list[str] = []
            stdout_buffer = ""
            command = "bash /workspace/execute_task.sh"

            async for stream_type, content in self._async_stream_execute(
                container.id,
                command,
                timeout=_settings.skills.sandbox_timeout,
            ):
                if stream_type == "error":
                    destroy_container = True
                    yield self._format_sse_event("error", {"message": content})
                    return

                if stream_type == "stderr":
                    stderr_text = content.strip()
                    if stderr_text:
                        logger.warning(f"{log_prefix} Sandbox stderr: {stderr_text}")
                    continue

                if stream_type != "stdout":
                    continue

                stdout_buffer += content
                while "\n" in stdout_buffer:
                    line, stdout_buffer = stdout_buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                    except (json.JSONDecodeError, ValueError):
                        logger.debug(f"{log_prefix} Sandbox stdout: {line}")
                        continue

                    event_type = event.get("type", "")

                    if event_type == "assistant" and "message" in event:
                        msg = event["message"]
                        if isinstance(msg, dict):
                            content_blocks = [
                                block
                                for block in msg.get("content", [])
                                if isinstance(block, dict)
                            ]
                            has_tool_use = any(
                                block.get("type") == "tool_use"
                                for block in content_blocks
                            )
                            for block in content_blocks:
                                if block.get("type") == "thinking":
                                    thinking_text = block.get("thinking", "") or block.get("text", "")
                                    if thinking_text:
                                        brief = (
                                            thinking_text[:120].replace("\n", " ") + "..."
                                            if len(thinking_text) > 120
                                            else thinking_text.replace("\n", " ")
                                        )
                                        yield self._format_sse_event(
                                            "thinking", {"message": brief}
                                        )
                                elif block.get("type") == "text":
                                    text = block.get("text", "")
                                    if text:
                                        if has_tool_use:
                                            yield self._format_sse_event(
                                                "status",
                                                {
                                                    "step": "planning",
                                                    "message": text.strip(),
                                                },
                                            )
                                        else:
                                            full_output.append(text)
                                            yield self._format_sse_event(
                                                "token", {"delta": text}
                                            )
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
                        yield self._format_sse_event(
                            "tool_use", {"tool": tool_name, "message": label}
                        )
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
                            yield self._format_sse_event(
                                "token", {"delta": result_text}
                            )
                    elif event_type == "system":
                        msg = event.get("message", "")
                        if msg:
                            yield self._format_sse_event(
                                "status", {"step": "system", "message": msg}
                            )

            remaining_stdout = stdout_buffer.strip()
            if remaining_stdout:
                try:
                    event = json.loads(remaining_stdout)
                except (json.JSONDecodeError, ValueError):
                    logger.debug(f"{log_prefix} Sandbox stdout: {remaining_stdout}")
                else:
                    if event.get("type") == "result" and event.get("result") and not full_output:
                        result_text = event["result"]
                        full_output.append(result_text)
                        yield self._format_sse_event(
                            "token", {"delta": result_text}
                        )

            result = "".join(full_output)
            self.update_sandbox_progress(db_session, sandbox.id, 100, "busy")

            output_files = self.docker_manager.collect_output_files(sandbox.sandbox_index)
            result_dir = self.docker_manager._get_result_dir(sandbox.sandbox_index)
            if not output_files:
                logger.warning(
                    f"{log_prefix} Skill execution completed but no deliverable files were found "
                    f"in sandbox result directory"
                )

            file_attachments = []
            for file_info in output_files:
                blob_url: str | None = None
                blob_key: str | None = None
                content_type = (
                    mimetypes.guess_type(file_info["name"])[0]
                    or "application/octet-stream"
                )
                try:
                    file_path = result_dir / file_info["name"]
                    if not file_path.is_file():
                        continue

                    blob_key = (
                        f"skill-outputs/{user_id}/{conversation_id}/"
                        f"{uuid.uuid4().hex}_{file_info['name']}"
                    )
                    with open(file_path, "rb") as file_data:
                        blob_storage_client.upload_bytes(
                            blob_path=blob_key,
                            data=file_data,
                            content_type=content_type,
                        )
                    blob_url = blob_storage_client.generate_sas_url(
                        blob_key,
                        expiry_hours=24,
                    )
                    logger.info(f"{log_prefix} Uploaded sandbox result file to blob: {blob_key}")
                    file_path.unlink(missing_ok=True)
                except Exception as blob_exc:
                    logger.warning(f"{log_prefix} Failed to upload sandbox result file to blob: {blob_exc}")
                    continue

                output_payload = {
                    "name": file_info["name"],
                    "size": file_info["size"],
                    "sandbox_index": sandbox.sandbox_index,
                    "download_url": f"/skills/sandboxes/{sandbox.sandbox_index}/files/{file_info['name']}",
                    "blob_url": blob_url,
                    "blob_path": blob_key,
                    "content_type": content_type,
                }
                file_attachments.append(output_payload)
                yield self._format_sse_event("file", output_payload)

            message_content = result or "Execution completed without textual output."
            if file_attachments:
                message_content += f"\n\nGenerated {len(file_attachments)} file(s):"
                for attachment in file_attachments:
                    message_content += (
                        f"\n- {attachment['name']} ({attachment['size']:,} bytes)"
                    )

            primary_attachment = next(
                (
                    attachment
                    for attachment in file_attachments
                    if attachment.get("blob_path")
                ),
                None,
            )

            assistant_message, _ = conversation_service.add_message(
                request,
                db_session,
                user_id,
                conversation_id,
                ConversationMessageCreateRequest(
                    role="assistant",
                    content=message_content,
                    blob_path=primary_attachment.get("blob_path") if primary_attachment else None,
                    blob_name=primary_attachment.get("name") if primary_attachment else None,
                    blob_content_type=primary_attachment.get("content_type") if primary_attachment else None,
                    blob_size=primary_attachment.get("size") if primary_attachment else None,
                ),
            )
            logger.info(
                f"{log_prefix} Persisted skill assistant message id={assistant_message.id} "
                f"blob_path={assistant_message.blob_path}"
            )

            yield self._format_sse_event(
                "done",
                {
                    "output": result,
                    "files": file_attachments,
                },
            )
        except Exception as exc:
            destroy_container = True
            logger.error(f"{log_prefix} Error executing skill: {exc}")
            try:
                conversation_service.add_message(
                    request,
                    db_session,
                    user_id,
                    conversation_id,
                    ConversationMessageCreateRequest(
                        role="assistant",
                        content=f"Execution failed: {str(exc)}",
                    ),
                )
            except Exception:
                logger.warning(f"{log_prefix} Failed to persist skill execution error to conversation")
            yield self._format_sse_event("error", {"message": str(exc)})
        finally:
            try:
                self.docker_manager.reset_workspace(sandbox.sandbox_index)
            except Exception as cleanup_exc:
                logger.warning(f"{log_prefix} Failed to clean up sandbox workspace: {cleanup_exc}")
                destroy_container = True

            self.release_sandbox(
                db_session,
                sandbox.id,
                destroy_container=destroy_container,
                progress=100,
            )

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
