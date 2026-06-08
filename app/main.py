import traceback
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from scalar_fastapi import get_scalar_api_reference
from app.services.prediction_service import predictor_service
from app.api.v1.api import api_router
from app.core.config import settings

# ตั้งค่า Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up FastAPI application...")
    predictor_service.load_models()
    yield
    print("Shutting down FastAPI application...")


app = FastAPI(title="fastapi", lifespan=lifespan)

# Middleware สำหรับดักจับ Error และแสดง Log
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.error(f"Global Error Catch: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal Server Error",
                "traceback": traceback.format_exc() if settings.DEBUG else None
            }
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
