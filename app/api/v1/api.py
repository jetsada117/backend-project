from fastapi import APIRouter
from app.api.v1.endpoints import auth, predictions

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(
    predictions.router, prefix="/predictions", tags=["predictions"]
)
