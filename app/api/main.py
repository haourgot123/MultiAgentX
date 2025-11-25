from fastapi import FastAPI, APIRouter, status
from app.agent.api.routes.agents import router as agents_router
from app.agent.api.routes.files import router as files_router
from app.agent.api.routes.migrate import router as migrate_router
from app.agent.api.routes.experience import router as experience_router
from app.agent.api.settings import api_settings
from starlette.middleware.cors import CORSMiddleware

v2_router = APIRouter(prefix="/api")
v2_router.include_router(agents_router)
v2_router.include_router(files_router)
v2_router.include_router(experience_router)
v2_router.include_router(migrate_router)

def create_app() -> FastAPI:
    app = FastAPI(
        title=api_settings.title,
        version=api_settings.version,
        docs_url="/docs" if api_settings.docs_enabled else None,
        redoc_url="/redoc" if api_settings.docs_enabled else None,
        openapi_url="/openapi.json" if api_settings.docs_enabled else None,
    )
    app.include_router(v2_router)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.get("/health", status_code=status.HTTP_200_OK, description="Health check")
    async def get_health():
        return {"status": "success"}
    
    return app

app = create_app()
