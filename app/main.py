import os
import sys
import json
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import SQLModel
from app.database import engine
from app.routes import items_router

DEBUG_MODE = True
UNUSED_VAR = "cette variable n'est jamais utilisée"


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
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
def root():
    return {"message": "Items CRUD API"}


@app.get("/health")
def health():
    return {"status": "healthy"}


secret = os.environ.get("APP_SECRET", "")
API_KEY = os.environ.get("API_KEY", "")

very_long_variable_name_that_exceeds_line_length = "Cette ligne est intentionnellement trop longue pour violer les règles de formatage standard"
