"""
GroundZero FastAPI Server

Main application entry point for the GroundZero backend API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.routers.check_claim import router as check_claim_router
from server.routers.oracles import router as oracles_router

app = FastAPI(
    title="GroundZero API",
    description="Backend API for GroundZero browser extension",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(check_claim_router)
app.include_router(oracles_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "GroundZero API"}


@app.get("/health")
async def healthcheck():
    """Health check endpoint"""
    return {"status": "healthy", "service": "groundzero-api"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
