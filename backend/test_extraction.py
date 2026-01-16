"""Test script for running parallel extraction on tesla.db"""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from engines.inference import run_parallel_extraction
from engines.inference.db import get_db_connection


async def main():
    db_path = os.path.join(os.path.dirname(__file__), "reports", "openai.db")
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return
    
    print(f"Running extraction on: {db_path}")
    
    async with get_db_connection(db_path) as db:
        results = await run_parallel_extraction(db)
        print(f"\nExtraction complete. Total results: {len(results)}")
        
        # Print summary
        total_triplets = sum(len(r.triplets) for r in results)
        print(f"Total triplets extracted: {total_triplets}")


if __name__ == "__main__":
    asyncio.run(main())
