"""Configuration de la base de données et gestion des sessions.

Ce module gère la connexion à la base de données PostgreSQL
et fournit une fonction générateur pour obtenir des sessions de base de données.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlmodel import Session, create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Configure it in your environment or in a .env file."
    )

POOL_SIZE = 10

engine = create_engine(DATABASE_URL)


def get_db():
    with Session(engine) as session:
        yield session
