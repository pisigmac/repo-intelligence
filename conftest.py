import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from libs.common.db import Base

TEST_DB_URL = "postgresql+asyncpg://repo:repo@localhost/repo_intelligence"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
