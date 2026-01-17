import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.revision.view import database_router
from backend.api.token.view import token_router
from backend.api.user.view import authentication_router
from backend.exceptions.model import BusinessBaseException
from backend.exceptions.handler import exception_handler, global_exception_handler


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(BusinessBaseException, exception_handler)
app.add_exception_handler(Exception, global_exception_handler)
app.include_router(authentication_router)
app.include_router(database_router)
app.include_router(token_router)    


@app.get("/")
async def root():
    return {"message": "Hello World"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
