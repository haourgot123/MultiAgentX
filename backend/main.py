import uvicorn
from fastapi import FastAPI

from backend.api.revision.view import database_router
from backend.api.token.view import token_router
from backend.api.user.view import authentication_router

app = FastAPI()

app.include_router(authentication_router)
app.include_router(database_router)
app.include_router(token_router)


@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
