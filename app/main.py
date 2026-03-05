from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from scalar_fastapi import get_scalar_api_reference
from app.services.prediction_service import predictor_service
from app.api.v1.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up FastAPI application...")
    predictor_service.load_models()
    yield
    print("Shutting down FastAPI application...")


app = FastAPI(title="fastapi", lifespan=lifespan)

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
