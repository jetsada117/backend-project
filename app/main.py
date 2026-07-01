import traceback
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone


from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from scalar_fastapi import get_scalar_api_reference
from app.services.prediction_service import predictor_service
from app.api.v1.api import api_router
from app.core.config import settings

logger = logging.getLogger("uvicorn")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up FastAPI application...")
    predictor_service.load_models()
    yield
    print("Shutting down FastAPI application...")


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)


import time


@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    start_time = time.perf_counter()
    request_time = datetime.now(timezone.utc).isoformat(timespec="milliseconds")
    try:
        response = await call_next(request)
        process_time = time.perf_counter() - start_time

        logger.info(
            f"[{request_time}] IP: {request.client.host} | Method: {request.method} | "
            f"Path: {request.url.path} | Status: {response.status_code} | "
            f"Taken: {process_time:.4f}s"
        )

        response.headers["X-Process-Time"] = f"{process_time:.4f}s"
        return response
    except Exception as exc:
        logger.error(f"[{request_time}] Global Error Catch: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal Server Error",
                "traceback": traceback.format_exc() if settings.DEBUG else None,
            },
        )


app.include_router(api_router, prefix="/api/v1")


@app.get("/", response_class=PlainTextResponse)
def index():
    return "Hello World!!"


@app.head("/", response_class=PlainTextResponse)
def index_head():
    return "Hello World!!"


# Path: /scalar
@app.get("/scalar", include_in_schema=False)
async def scalar_html():
    return get_scalar_api_reference(
        openapi_url=app.openapi_url,
        title=app.title,
    )
