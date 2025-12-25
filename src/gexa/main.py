"""
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from gexa import __version__
from gexa.config import settings
from gexa.database.schemas import HealthResponse, ErrorResponse
from gexa.api.routes import search, contents, crawl, findsimilar, answer, keys


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    print(f"🚀 Starting GEXA API v{__version__}")
    print(f"📊 Database: {settings.database_url.split('@')[-1]}")
    print(f"🔧 Debug mode: {settings.api_debug}")
    
    yield
    
    # Shutdown
    print("👋 Shutting down GEXA API")


app = FastAPI(
    title="GEXA API",
    description="Web Search API for AI Agents - Similar to Exa.ai",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": str(exc) if settings.api_debug else "An internal error occurred",
        },
    )


# Health check endpoint
@app.get("/", response_model=HealthResponse, tags=["Health"])
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        timestamp=datetime.utcnow(),
    )


# Include routers
app.include_router(search.router, prefix="/search", tags=["Search"])
app.include_router(contents.router, prefix="/contents", tags=["Contents"])
app.include_router(crawl.router, prefix="/crawl", tags=["Crawl"])
app.include_router(findsimilar.router, prefix="/findsimilar", tags=["Find Similar"])
app.include_router(answer.router, prefix="/answer", tags=["Answer"])
app.include_router(keys.router, prefix="/keys", tags=["API Keys"])


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "gexa.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug,
    )
