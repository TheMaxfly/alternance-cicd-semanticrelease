from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from sqlmodel import SQLModel

from app.database import engine
from app.routes import items_router


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> Any:
    SQLModel.metadata.create_all(engine)
    yield


app = FastAPI(
    title="Items CRUD API",
    description="API pour gérer une liste d'articles",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(items_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Items CRUD API"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
