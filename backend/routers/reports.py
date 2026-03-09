"""Reports router — lists available analysis databases."""

import glob
import os

from fastapi import APIRouter

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("")
async def list_reports():
    """List all completed analysis reports (one per .db file in the working directory).

    Each report corresponds to a query that was previously analysed and whose
    results were persisted to a SQLite file.

    Returns:
        List of objects with ``name`` (human-readable) and ``db_path`` (filename).
    """
    db_files = sorted(glob.glob("*.db"))
    return [
        {"name": os.path.splitext(f)[0], "db_path": f}
        for f in db_files
    ]
