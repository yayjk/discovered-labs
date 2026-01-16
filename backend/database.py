import aiosqlite
from contextlib import asynccontextmanager

DB_PATH = "reports/tesla.db"


@asynccontextmanager
async def get_db_connection(db_path: str = DB_PATH):
    """Create and return a database connection as an async context manager."""
    db = await aiosqlite.connect(db_path)
    try:
        yield db
    finally:
        await db.close()
