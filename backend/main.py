import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.meta.view import router as meta_router
from backend.api.revision.view import database_router
from backend.api.token.view import router as token_router
from backend.api.user.view import router as user_router
from backend.exceptions.handler import exception_handler, global_exception_handler
from backend.exceptions.model import BusinessBaseException

main_router = APIRouter(prefix="/api")
main_router.include_router(token_router)
main_router.include_router(database_router)
main_router.include_router(user_router)
main_router.include_router(meta_router)
app = FastAPI(
    title="MultiAgentX API",
    description="API for the MultiAgentX application",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(BusinessBaseException, exception_handler)
app.add_exception_handler(Exception, global_exception_handler)
app.include_router(main_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
