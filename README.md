# Backend Project: AI Facial Feature Prediction API

This project is a RESTful API backend built with **FastAPI** to serve deep learning models for facial feature prediction. It utilizes **PostgreSQL** for data storage, **SQLAlchemy** for ORM, and **Alembic** for database migrations.

## 🚀 Features

* **RESTful API:** Built with high-performance FastAPI.
* **Asynchronous Database Operations:** Uses `asyncpg` for non-blocking database interactions.
* **AI Model Serving:** Integrates multiple TensorFlow/Keras `.keras` models for predicting age, gender, hair color, hair style, eyebrows, skin type, and beard presence.
* **Concurrent Predictions:** Employs `ThreadPoolExecutor` and `asyncio.gather` to run multiple models simultaneously for faster response times.
* **Database Migrations:** Managed via Alembic.
* **Interactive API Documentation:** Provided by Scalar.

## 🛠️ Technology Stack

* **Python:** 3.10+ (Recommended 3.13)
* **Framework:** FastAPI
* **Package Manager:** uv
* **Database:** PostgreSQL
* **Database Driver:** asyncpg
* **ORM:** SQLAlchemy (Async)
* **Migration:** Alembic
* **Data Validation:** Pydantic
* **ASGI Server:** Uvicorn
* **Machine Learning:** TensorFlow / Keras

## 📂 Project Structure

```plaintext
backend-project/
├── alembic/                    # โฟลเดอร์ที่ Auto Generate มาจาก Alembic
├── app/                        # โฟลเดอร์หลักเก็บ Source Code
│   ├── api/                    # API Routers and endpoints
│   ├── core/                   # การตั้งค่าหลัก (เช่น config.py โหลด .env)
│   ├── db/                     # Database session (Engine, SessionLocal)
│   ├── models/                 # SQLAlchemy database models
│   ├── schemas/                # Pydantic models (Request/Response validation)
│   └── services/               # Business logic และ AI Prediction Service
├── app/machine_models/         # โฟลเดอร์เก็บไฟล์โมเดล AI (.keras) - **ห้ามเอาขึ้น Git**
├── alembic.ini                 # Alembic configuration
├── .env                        # ตัวแปรระบบ (Database URL, Secret Keys)
├── .gitignore                  # ไฟล์ที่ไม่ต้องการเอาขึ้น Git
├── pyproject.toml              # ไฟล์จัดการ Package ของ uv
└── main.py                     # จุดเริ่มต้นของโปรแกรม (Entry Point)