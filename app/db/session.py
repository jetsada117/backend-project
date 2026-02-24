from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.core.config import settings

# 1. สร้าง Async Engine
from sqlalchemy.ext.asyncio import create_async_engine

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    # --- ส่วนที่ควรเพิ่มเพื่อความเร็ว ---
    pool_size=10,  # สร้างการเชื่อมต่อรอไว้เลย 10 ท่อ
    max_overflow=20,  # หากงานเยอะ ขยายเพิ่มได้อีก 20 ท่อ
    pool_timeout=30,  # ถ้ารอนานเกิน 30 วินาทีให้ Error (ป้องกันแอปค้าง)
    # -----------------------------
    pool_pre_ping=True,
    pool_recycle=3600,
)

# 2. สร้าง Session Factory
SessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)


# 3. Dependency สำหรับใช้ใน API Endpoint (Dependency Injection)
async def get_db():
    async with SessionLocal() as session:
        yield session
