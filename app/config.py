from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.models import Base
import os
from dotenv import load_dotenv
from fastapi import Depends
import asyncio
import logging

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in environment variables")

SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "False").lower() == "true"

engine = create_async_engine(DATABASE_URL, echo=SQLALCHEMY_ECHO)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db(max_attempts: int = 5, delay: int = 2):
    attempt = 0
    while attempt < max_attempts:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database initialized successfully")
            return
        except Exception as e:
            attempt += 1
            logger.warning(f"Failed to initialize database (attempt {attempt}/{max_attempts}): {e}")
            if attempt == max_attempts:
                logger.error("Max attempts reached, database initialization failed")
                raise
            await asyncio.sleep(delay)

async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()