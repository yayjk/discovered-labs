from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import relationships_router, analysis_router, reports_router

app = FastAPI(title="Signal Graph API", description="API for Company Relationship Graphs and Analysis", version="1.0.0", root_path=os.getenv("ROOT_PATH", ""))

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(relationships_router)
app.include_router(analysis_router)
app.include_router(reports_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Discovered Labs API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
