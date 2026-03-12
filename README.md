# MultiAgentX

MultiAgentX is a full-stack multi-agent chat platform with file-centric workflows and a RAG ingestion pipeline.

This repository includes:
- A FastAPI backend
- A React + Vite frontend
- PostgreSQL for transactional data
- Milvus for vector search
- Docling-based document extraction (text + bounding boxes)

## Key Features

- User authentication (login/register/token)
- Conversation management
  - Normal chat
  - File chat (attach files to conversations)
- File management
  - Upload, list, rename, download, delete
  - Office files (`.docx`, `.xlsx`, `.pptx`, etc.) are converted to PDF via LibreOffice (`soffice`)
- RAG data ingestion pipeline
  - Parse document with Docling
  - Extract text + page + bbox metadata
  - Chunking
  - Embedding with OpenAI `text-embedding-3-large`
  - Store vectors in Milvus
- Ingestion status tracking per file (`pending`, `processing`, `completed`, `failed`)

## System Architecture

```text
Frontend (React/Vite/Zustand)
        |
        v
Backend API (FastAPI)
  |        |                 \
  |        |                  \
  v        v                   v
PostgreSQL Local file storage  Milvus
(transactional) (tmp/uploads)  (vector DB)

Background ingestion flow (after upload):
File -> Docling parse (text+bbox) -> Chunking -> OpenAI Embedding -> Milvus upsert
```

## Repository Structure

```text
MultiAgentX/
  alembic/                  # DB migrations
  backend/
    api/
      token/                # auth endpoints
      user/                 # user endpoints
      files/                # file management
      conversation/         # conversations + messages
      data_ingestion/       # Docling + embedding + Milvus
      meta/                 # metadata endpoints
      revision/             # migration endpoints (admin)
    config/
    databases/
    main.py                 # FastAPI app entry
  frontend/
    src/
      components/
      pages/
      store/                # Zustand stores
      lib/api.ts            # API client
  docker-compose.yaml       # Redis, Postgres, Milvus stack
  requirements.txt          # Python dependencies
```

## Prerequisites

- Python 3.11+ (3.11/3.12 recommended)
- Node.js 18+
- npm 9+
- Docker + Docker Compose
- LibreOffice (`soffice`) installed on host machine
- (Recommended for OCR-heavy PDFs) Tesseract available for Docling OCR pipeline

## Quick Start

### 1) Clone and prepare environment

```bash
git clone <your-repo-url>
cd MultiAgentX
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

### 2) Configure environment variables

Create/update `.env` in repository root:

```env
ENV=DEV
LOG_LEVEL=DEBUG
LOG_FILE=logs/backend.log
# LOG_LEVEL supported values: TRACE, DEBUG, INFO, SUCCESS, WARNING, ERROR, CRITICAL

# HTTP middleware
MIDDLEWARE_REQUEST_LOGGING_ENABLED=true
MIDDLEWARE_RATE_LIMIT_ENABLED=true
MIDDLEWARE_RATE_LIMIT_REQUESTS=120
MIDDLEWARE_RATE_LIMIT_WINDOW_SECONDS=60
MIDDLEWARE_RATE_LIMIT_EXCLUDED_PATHS=/docs,/redoc,/openapi.json,/socket.io,/healthz
MIDDLEWARE_RATE_LIMIT_TRUST_X_FORWARDED_FOR=true
MIDDLEWARE_SECURITY_HEADERS_ENABLED=true

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5435
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=multiagentx

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=replace_me

# Azure OpenAI GPT-5.1
AZURE-OPENAI-GPT51-ENDPOINT=
AZURE-OPENAI-GPT51-API-KEY=
AZURE-OPENAI-GPT51-API-VERSION=2025-04-01-preview
AZURE-OPENAI-GPT51-DEPLOYMENT-NAME=gpt-5.1

# Azure OpenAI embeddings
AZURE-OPENAI-EMBEDDING-ENDPOINT=
AZURE-OPENAI-EMBEDDING-KEY=
AZURE-OPENAI-EMBEDDING-DEPLOYMENT-NAME=text-embedding-3-large
AZURE-OPENAI-EMBEDDING-API-VERSION=2023-05-15
OPENAI_EMBEDDING_DIMENSION=3072
OPENAI_EMBEDDING_BATCH_SIZE=32
OPENAI_EMBEDDING_TIMEOUT_SECONDS=120

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION_NAME=document_chunks
MILVUS_METRIC_TYPE=COSINE
MILVUS_INDEX_TYPE=IVF_FLAT
MILVUS_INDEX_NLIST=1024
MILVUS_CONSISTENCY_LEVEL=Strong
```

### 3) Start infrastructure services

```bash
docker compose up -d redis pgvector etcd minio milvus
```

Default ports:
- PostgreSQL: `5435`
- Redis: `6379`
- Milvus: `19530`
- Milvus health/API: `9091`
- MinIO: `9000` (API), `9001` (console)

### 4) Run database migrations

```bash
alembic upgrade head
```

### 5) Start backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs:
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 6) Start frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend default URL:
- `http://localhost:5173`

Set backend base URL for frontend if needed:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

## API Overview

Base prefix: `/api`

### Authentication
- `POST /authentication/login`
- `POST /authentication/register`
- `POST /authentication/access`

### Files
- `GET /files`
- `POST /files/upload`
- `PATCH /files/{file_id}`
- `GET /files/{file_id}/download`
- `DELETE /files/{file_id}`

### Conversations
- `GET /conversations`
- `POST /conversations`
- `GET /conversations/{conversation_id}`
- `PATCH /conversations/{conversation_id}`
- `DELETE /conversations/{conversation_id}`
- `PUT /conversations/{conversation_id}/files`
- `POST /conversations/{conversation_id}/messages`

### Data Ingestion
- `GET /ingestion/files/{file_id}/status`
- `POST /ingestion/files/{file_id}/run`
- `POST /ingestion/files/run`
- `GET /ingestion/collections` (list Milvus collections)
- `GET /ingestion/chunks` (query: `user_id?`, `file_id?`, `limit`, `offset`)
- `GET /ingestion/files/{file_id}/chunks` (query: `limit`, `offset`)

### Meta
- `GET /meta/phone-countries`

### User / Revision
- `/user/*` endpoints (token required)
- `/revision/*` endpoints (admin only)

## Upload and Ingestion Flow

1. User uploads one or more files via `POST /api/files/upload`
2. Backend saves files to local storage (`tmp/uploads/{user_id}/...`)
3. If uploaded file is office format, backend converts it to PDF using LibreOffice
4. Backend creates `FileAsset` records with ingestion status `pending`
5. Ingestion runs when client explicitly calls ingestion run API
6. Ingestion service:
   - Extracts document blocks using Docling
   - Reads text, page number, and bounding boxes
   - Builds chunks with overlap
   - Calls OpenAI embeddings (`text-embedding-3-large`)
   - Upserts vectors into Milvus
7. File status is updated to `completed` or `failed`

## Milvus Collection Schema (Current)

Collection name: from `MILVUS_COLLECTION_NAME` (default `document_chunks`)

Stored fields include:
- `id` (`{user_id}:{file_id}:{chunk_index}`)
- `user_id`
- `file_id`
- `chunk_index`
- `page_no`
- `file_name`
- `mime_type`
- `text`
- `bbox` (JSON string payload of source bounding boxes)
- `metadata_json` (JSON metadata for filter/rerank contexts, including `user_id`, `file_id`, `file_name`, `mime_type`, `chunk_index`, `page_no`)
- `created_unix`
- `vector` (float vector, dim=3072 by default)

## Development Commands

Backend checks:

```bash
python -m compileall backend alembic
pytest backend/api/tests -q
```

Frontend checks:

```bash
cd frontend
npm run lint
npm run build
```

## Troubleshooting

### `LibreOffice is not installed`
Install LibreOffice and ensure `soffice` is in PATH.

### `Docling is not installed`
Reinstall dependencies:

```bash
pip install -r requirements.txt
```

### `Milvus client is not installed`
Ensure `pymilvus` is installed (included in `requirements.txt`).

### Ingestion stays `failed`
- Check backend logs
- Check OpenAI API key and quota
- Check Milvus connectivity (`MILVUS_HOST`, `MILVUS_PORT`)
- Check file exists in local storage path

### Frontend cannot call backend
- Verify `VITE_API_BASE_URL`
- Verify backend is running on `:8000`
- Verify token is present in request headers

## Security Notes

- Do not commit real API keys to source control.
- Rotate any key that has ever been exposed in plain text.
- Use separate credentials for local/dev/prod.

## Current Scope and Limitations

- Conversation message endpoint currently stores messages; full LLM response orchestration is not yet implemented server-side.
- RAG indexing is implemented; retrieval + grounded answer generation pipeline should be added in chat runtime for end-to-end QA.

---

If you need, this README can be split into:
- `docs/backend.md`
- `docs/frontend.md`
- `docs/ingestion-rag.md`
- `docs/deployment.md`
for easier long-term maintenance.
