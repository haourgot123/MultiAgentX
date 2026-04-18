# MultiAgentX

MultiAgentX is a full-stack multi-agent chat platform with normal chat, file chat, RAG ingestion, long-term memory, and skill execution in Docker sandboxes.

The codebase currently consists of:

- A `FastAPI` backend with LangGraph-based agents
- A `React 19 + Vite + Zustand` frontend
- `PostgreSQL` for transactional data
- `Milvus` for vector search
- `Redis` for middleware/runtime support
- `Azure Blob Storage` for uploaded files, skills, and generated artifacts
- `Socket.IO` for ingestion/sandbox status updates
- `SSE` for chat and skill execution streaming

## What The App Does

- Auth flow with register, login, refresh token, logout, and self-service profile endpoints
- Normal chat with agent routing
- File chat backed by ingestion + retrieval
- Web search, deep research, and image generation routes through dedicated agents
- Long-term memory via `mem0` stored in Milvus
- File upload, rename, download, delete, and per-file ingestion tracking
- Office document upload with automatic PDF conversion via `soffice`
- Skill upload (`.md` or `.zip`), selection, execution, sandbox inspection, and artifact download
- Retrieval record storage for citation metadata and PDF highlighting

## Agent Overview

The backend currently includes these agent graphs:

- `general_agent`
- `rag_agent`
- `websearch_agent`
- `deep_research_agent`
- `image_generation_agent`

The general agent acts as the main router for regular chat requests.

## Architecture

```text
Frontend (React/Vite/Zustand)
  |-- REST -> FastAPI (/api/*)
  |-- SSE  -> conversation chat + skill execution streams
  |-- Socket.IO -> ingestion status + sandbox activity
  |
  v
Backend
  |-- LangGraph agents
  |-- SQLAlchemy models/services
  |-- Mem0 client
  |-- Blob storage client
  |
  +--> PostgreSQL
  +--> Redis
  +--> Milvus
  +--> Azure OpenAI / Azure OpenAI Image
  +--> Azure Blob Storage
  +--> Docker sandbox containers for skill execution
```

## Repository Layout

```text
MultiAgentX/
├── backend/
│   ├── agents/               # LangGraph agents and prompts
│   ├── api/                  # REST endpoints by domain
│   ├── config/               # Environment-backed settings
│   ├── databases/            # SQLAlchemy engine/session
│   ├── memory/               # Mem0 integration
│   ├── middleware/           # Request logging, rate limit, security headers
│   ├── realtime/             # Socket.IO integration
│   ├── utils/                # Auth, blob storage, logging, helpers
│   ├── main.py               # FastAPI entrypoint
│   └── cli.py                # Database/server CLI helpers
├── frontend/
│   ├── src/
│   │   ├── components/       # Chat, PDF, user, UI components
│   │   ├── layout/           # Application shell
│   │   ├── lib/              # API client and helpers
│   │   ├── pages/            # Files, file chat, agent skills
│   │   └── store/            # Zustand stores
│   └── e2e/                  # Playwright tests
├── alembic/                  # DB migrations
├── tests/                    # Root-level integration and utility tests
├── docker-compose.yaml       # Redis, Postgres, etcd, MinIO, Milvus
└── requirements.txt          # Backend dependencies
```

## Prerequisites

- Python `3.11+`
- Node.js `18+`
- npm
- Docker and Docker Compose
- LibreOffice (`soffice`) if you want Office files auto-converted to PDF
- Access to:
  - Azure OpenAI chat deployment
  - Azure OpenAI embedding deployment
  - Azure Blob Storage
- Optional access to:
  - Azure OpenAI image deployment
  - Tavily or Google Search API for web search
  - Anthropic or Azure Anthropic credentials for skill execution

## Environment Setup

The backend reads environment variables from the repository root `.env`.

The example below covers the variables needed for the main local flow:

```env
ENV=DEV
LOG_LEVEL=INFO
LOG_FILE=logs/backend.log

POSTGRES_HOST=localhost
POSTGRES_PORT=5435
POSTGRES_USER=postgres
POSTGRES_PASSWORD=haonn
POSTGRES_DB=multiagentx

REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=replace_me

AZURE-OPENAI-GPT51-ENDPOINT=
AZURE-OPENAI-GPT51-API-KEY=
AZURE-OPENAI-GPT51-API-VERSION=2025-04-01-preview
AZURE-OPENAI-GPT51-DEPLOYMENT-NAME=gpt-5.1

AZURE-OPENAI-EMBEDDING-ENDPOINT=
AZURE-OPENAI-EMBEDDING-KEY=
AZURE-OPENAI-EMBEDDING-API-VERSION=2023-05-15
AZURE-OPENAI-EMBEDDING-DEPLOYMENT-NAME=text-embedding-3-large
OPENAI_EMBEDDING_DIMENSION=3072

MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION_NAME=document_chunks

MEM0_ENABLE_LONG_TERM_MEMORY=true
MEM0_MILVUS_COLLECTION=user_memories

BLOB-CONNECTION-STRING=
BLOB-CONTAINER=
AZURE-ACCOUNT-NAME=
AZURE-ACCOUNT-KEY=

AZURE-OPENAI-IMAGE-ENDPOINT=
AZURE-OPENAI-IMAGE-API-KEY=

TAVILY_SEARCH_API_KEY=

SKILLS_ENABLE_SANDBOX=true
SKILLS_MAX_SANDBOXES=10
SANDBOX_IMAGE=multiagentx-sandbox:latest
```

Notes:

- The checked-in `docker-compose.yaml` exposes PostgreSQL on port `5435` and uses password `haonn`.
- The backend accepts several Azure variable aliases with either hyphenated or underscored names. The definitions live in `backend/config/config.py`.
- File upload/download and persisted skill artifacts rely on Azure Blob Storage configuration.
- Skill execution requires a running Docker daemon and valid model credentials for the skill runtime.

For the frontend, create `frontend/.env` if you need non-default endpoints:

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_SOCKET_BASE_URL=http://localhost:8000
```

## Local Development

### 1. Install backend dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start infrastructure

```bash
docker compose up -d redis postgres etcd minio milvus
```

Default local ports from `docker-compose.yaml`:

- PostgreSQL: `5435`
- Redis: `6379`
- Milvus: `19530`
- Milvus health/API: `9091`
- MinIO API: `9000`
- MinIO console: `9001`

### 3. Run database migrations

```bash
alembic upgrade head
```

### 4. Start the backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Docs:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend default URL:

- `http://localhost:5173`

## Useful Commands

### Backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
pytest backend/api/tests -q
pytest backend/agents/tests -q
pytest tests -q
alembic upgrade head
python -m backend.cli database upgrade
```

### Frontend

```bash
cd frontend && npm run dev
cd frontend && npm run build
cd frontend && npm run lint
cd frontend && npm run test
cd frontend && npm run test:e2e
```

## Frontend Routes

The app currently exposes these main pages:

- `/` - main chat
- `/files` - file management
- `/chat-file` - file chat with citations/PDF context
- `/agent-skills` - skill management and sandbox execution
- `/login`
- `/register`

## API Surface

All backend routes are mounted under `/api`.

Authentication:

- `POST /authentication/register`
- `POST /authentication/login`
- `POST /authentication/access`

User:

- `GET /user/me?user_id={user_id}`
- `PUT /user/me/information?user_id={user_id}`
- `PUT /user/me/password?user_id={user_id}`
- `POST /user/logout?user_id={user_id}`

Files:

- `GET /files`
- `POST /files/upload`
- `PATCH /files/{file_id}`
- `GET /files/{file_id}/sas`
- `POST /files/sas`
- `GET /files/{file_id}/download`
- `DELETE /files/{file_id}`

Conversations:

- `GET /conversations`
- `POST /conversations`
- `GET /conversations/{conversation_id}`
- `PATCH /conversations/{conversation_id}`
- `DELETE /conversations/{conversation_id}`
- `PUT /conversations/{conversation_id}/files`
- `POST /conversations/{conversation_id}/messages`
- `POST /conversations/chat`
- `POST /conversations/deep-research/plan`
- `POST /conversations/deep-research/approve`
- `GET /conversations/{conversation_id}/messages/{message_id}/retrievals`

Data ingestion:

- `GET /ingestion/files/{file_id}/status`
- `POST /ingestion/files/{file_id}/run`
- `POST /ingestion/files/run`
- `GET /ingestion/collections`
- `GET /ingestion/chunks`
- `GET /ingestion/files/{file_id}/chunks`

Memory:

- `GET /memories`
- `POST /memories`
- `POST /memories/search`
- `PATCH /memories/{memory_id}`
- `DELETE /memories/{memory_id}`
- `DELETE /memories/clear/all`

Skills:

- `GET /skills`
- `POST /skills/upload`
- `PATCH /skills/{skill_id}`
- `DELETE /skills/{skill_id}`
- `POST /skills/select`
- `POST /skills/execute`
- `GET /skills/sandboxes/list`
- `GET /skills/sandboxes/{sandbox_index}/files`
- `GET /skills/sandboxes/{sandbox_index}/files/{filename}/preview`
- `GET /skills/sandboxes/{sandbox_index}/files/{filename}`
- `GET /skills/artifacts/{conversation_id}`
- `GET /skills/artifacts/{artifact_id}/download`

Other:

- `GET /meta/phone-countries`
- `POST /revision/upgrade` - admin only
- `POST /revision/downgrade` - admin only

## Streaming And Realtime Notes

- Chat responses use `text/event-stream`
- Skill execution also streams progress over `text/event-stream`
- File ingestion and sandbox updates use Socket.IO
- The frontend sends auth using the `Token` header, not `Authorization: Bearer`

## File And Ingestion Flow

1. Upload file through `/api/files/upload`
2. Backend stores file metadata in PostgreSQL and content in Azure Blob Storage
3. Office files are converted to PDF locally with LibreOffice before upload
4. Ingestion reads the blob back into a temp file
5. Docling extracts document structure and chunk metadata
6. Embeddings are generated and inserted into Milvus
7. File chat uses retrieval results and stores retrieval records for later highlighting

## Skill Flow

1. Upload a skill as `.md` or `.zip`
2. The backend extracts `SKILL.md`, stores metadata in PostgreSQL, and keeps a local working copy
3. The raw upload is also persisted to Blob Storage when configured
4. Selected skills can be executed in a Docker sandbox
5. Output files are exposed for preview/download and persisted as conversation artifacts

## Testing

Backend tests are split across:

- `backend/api/tests`
- `backend/agents/tests`
- `tests`

Frontend tests include:

- Vitest unit tests alongside components/stores
- Playwright E2E tests under `frontend/e2e`

## Current Implementation Notes

- `backend.main:app` is the correct ASGI target for local development
- Socket.IO is used for ingestion/sandbox state, not for assistant token streaming
- The skills page is a first-class feature in the current codebase and should be considered part of the main product surface
- Some legacy config classes still exist in `backend/config/config.py`, but the active stack is PostgreSQL + Milvus + Redis + Blob Storage
