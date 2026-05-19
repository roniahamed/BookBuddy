import time
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from loguru import logger
from jose import jwt, JWTError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.core.config import settings
from app.core.logging import setup_logging

# Initialize Limiter
limiter = Limiter(key_func=get_remote_address)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization")
        request.state.user = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(
                    token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
                )
                request.state.user = payload
            except JWTError:
                pass
                
        response = await call_next(request)
        return response

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info(f"Request: {request.method} {request.url.path}")
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        logger.info(f"Response: {response.status_code} (Duration: {duration:.4f}s)")
        return response

class I18nMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        lang = request.headers.get("Accept-Language", "").lower()
        # Only translate JSON responses if Hebrew is requested
        if lang.startswith("he") and response.headers.get("content-type") == "application/json":
            body = b""
            # Consume the original response body
            async for chunk in response.body_iterator:
                body += chunk
            
            try:
                import json
                from app.core.translation import translate_text
                
                data = json.loads(body.decode("utf-8"))
                
                def translate_recursive(obj):
                    if isinstance(obj, dict):
                        return {k: translate_recursive(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [translate_recursive(v) for v in obj]
                    elif isinstance(obj, str) and not obj.startswith("http") and not obj.endswith("Z") and len(obj) > 2:
                        return translate_text(obj, "he")
                    return obj
                
                translated_data = translate_recursive(data)
                return JSONResponse(
                    status_code=response.status_code, 
                    content=translated_data,
                    # don't pass headers as content-length will be wrong
                )
            except Exception as e:
                logger.error(f"I18n translation error: {e}")
                # Return original body if translation fails
                from fastapi.responses import Response
                return Response(
                    content=body, 
                    status_code=response.status_code, 
                    headers=dict(response.headers)
                )
        return response

def setup_middleware(app: FastAPI) -> None:
    # 1. Rate Limiting
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # 2. CORS Middleware
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # 3. Trusted Host Middleware
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=["*"]
    )

    # 4. GZip Middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # 5. Logging Middleware
    app.add_middleware(LoggingMiddleware)

    # 6. Authentication Middleware
    app.add_middleware(AuthMiddleware)

    # 6.5. I18n Middleware
    app.add_middleware(I18nMiddleware)

    # 7. Global Exception Logging (using a standard handler instead of middleware to avoid swallowing specific errors)
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        if isinstance(exc, StarletteHTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail}
            )
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"}
        )

    # 8. Custom Process Time Header
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
