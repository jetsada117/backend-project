from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

# 1. สร้าง Async Engine
engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
    "pool_recycle": 3600,
}

# SQLite ไม่รองรับ pool_size และ max_overflow
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
    })

engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# 2. สร้าง Session Factory
SessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)


# 3. Dependency สำหรับใช้ใน API Endpoint (Dependency Injection)
async def get_db():
    async with SessionLocal() as session:
        yield session
