from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.database import engine, Base
from app.core.middleware import setup_middleware
from app.core.logging import setup_logging
from app.router import api_router

# 1. Setup Logging
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    # Create database tables (if any models are imported)
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown logic

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# 2. Setup Middlewares
setup_middleware(app)

# 3. Include Routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME} API",
        "version": "1.0.0",
        "docs_url": "/docs"
    }
