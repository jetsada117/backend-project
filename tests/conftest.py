import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.api.deps import get_db
from app.db.base import Base

# --- Database Setup for Testing (Using SQLite In-memory) ---
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL)
TestSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine, class_=AsyncSession
)

@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

async def override_get_db() -> AsyncGenerator:
    async with TestSessionLocal() as session:
        yield session

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client() -> AsyncGenerator:
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator:
    async with TestSessionLocal() as session:
        yield session

# --- Global Mocks ---

@pytest.fixture(autouse=True)
def mock_external_services(mocker):
    # Mock Redis (OTP)
    mocker.patch("app.services.redis_service.save_otp", return_value=None)
    mocker.patch("app.services.redis_service.verify_otp", return_value=True)
    
    # Mock Email
    mocker.patch("app.services.email_service.send_otp_email", return_value=None)
    
    # Mock Storage (Cloudflare R2)
    mocker.patch(
        "app.services.storage_service.storage_service.upload_file", 
        return_value="https://mock-r2-url.com/image.jpg"
    )
    mocker.patch("app.services.storage_service.storage_service.delete_file", return_value=None)
    
    # Mock Predictor (Prevent loading models)
    mocker.patch("app.services.prediction_service.predictor_service.load_models", return_value=None)
    
    # Mock Predictor results
    mock_prediction = {
        "age_result": [0, 0, 1, 0, 0, 0],
        "gender_result": [0, 1],
        "haircolor_result": [0, 0, 1],
        "hairstyle_result": [1, 0],
        "eyebrows_result": [1, 0, 0, 0],
        "skin_result": [1, 0, 0, 0],
        "beard_result": [0, 0, 0, 0]
    }
    mocker.patch("app.services.prediction_service.predictor_service.predict_all", return_value=mock_prediction)
