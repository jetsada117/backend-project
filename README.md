---
title: Backend Project
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
---

# 🚀 Face Similarity API (FastAPI)

ยินดีต้อนรับสู่ระบบ Backend สำหรับวิเคราะห์และเปรียบเทียบใบหน้าครับ โปรเจกต์นี้ถูกออกแบบมาให้รันบน Hugging Face Spaces โดยใช้ Docker.

## 🛠️ Tech Stack
* **Framework:** FastAPI (Python 3.11).
* **Database:** SQLAlchemy (Raw SQL).
* **Security:** Argon2id & JWT Authentication.
* **ML Models:** ConvNeXt & InceptionV3.

## 💻 การพัฒนาและคำสั่งที่สำคัญ (Development Commands)

ในการพัฒนาโปรเจกต์นี้ เราใช้ `uv` สำหรับจัดการ Python environment และ dependencies:

### 1. การจัดการ Environment & Dependencies
* `uv sync`: ติดตั้ง dependencies ทั้งหมดที่ระบุในไฟล์ `pyproject.toml`.
* `uv add <package>`: เพิ่ม package ใหม่เข้าไปในโปรเจกต์.

### 2. การรันเซิร์ฟเวอร์ (Running Server)
* `uv run uvicorn app.main:app --reload`: รันเซิร์ฟเวอร์สำหรับพัฒนา (Development Server) โดยจะรีสตาร์ทอัตโนมัติเมื่อมีการแก้ไขโค้ด.
* `--host 0.0.0.0 --port 8000`: (ตัวเลือกเสริม) กำหนด host และ port.

### 3. การจัดการฐานข้อมูล (Database Migrations)
เราใช้ **Alembic** ในการควบคุมเวอร์ชันของฐานข้อมูล:
* `alembic upgrade head`: อัปเดตโครงสร้างฐานข้อมูล (Schema) ให้เป็นเวอร์ชันล่าสุด.
* `alembic revision --autogenerate -m "comment"`: สร้างไฟล์ migration ใหม่โดยอัตโนมัติจากการตรวจสอบความเปลี่ยนแปลงใน `models`.
* `alembic downgrade -1`: ย้อนกลับโครงสร้างฐานข้อมูลไป 1 เวอร์ชัน.

### 4. การทดสอบ (Testing)
* `pytest`: รันการทดสอบทั้งหมดในโฟลเดอร์ `tests/`.

## 🌐 System URLs
* **Live API (Production):** `https://jetsada117-backend-project.hf.space/`
* **Interactive Documentation (Scalar):** `https://jetsada117-backend-project.hf.space/scalar`
* **Alternative Documentation (Swagger UI):** `https://jetsada117-backend-project.hf.space//docs`

## 📊 Data Structure (25-Dimensional Vector)
ระบบจะแปลงผลลัพธ์จากการทำนายหรือคำบรรยายให้กลายเป็น Vector ขนาด 25 มิติ เพื่อใช้คำนวณความคล้ายคลึง (Similarity Score):
* **Age (6 มิติ):** [18-24, 25-34, 35-44, 45-54, 55-64, 65+]
* **Gender (2 มิติ):** [ชาย, หญิง]
* **Hair Color (3 มิติ):** [ดำ, น้ำตาล, อื่นๆ]
* **Hair Style (2 มิติ):** [สั้น, ยาว]
* **Eyebrows (4 มิติ):** แยกตามรูปทรงคิ้ว
* **Skin Tone (4 มิติ):** แยกตามเฉดสีผิว
* **Beard (4 มิติ):** แยกตามลักษณะหนวดเครา

## 🔒 Security & Performance
* **Authentication:** ใช้ **Argon2id** ในการแฮชรหัสผ่านและ **JWT (JSON Web Token)** สำหรับการเข้าถึงทรัพยากร.
* **OTP Verification:** ระบบส่งรหัสยืนยันตัวตนผ่าน Gmail SMTP เพื่อความปลอดภัยในการสมัครสมาชิก.
* **Cold Start Optimization:** มีระบบ Dummy Inference เพื่อวอร์มโมเดล (Warm-up) ทำให้ลดเวลาการประมวลผลครั้งแรกจาก 35 วินาที เหลือเพียง 3-4 วินาที.

## 🛡️ Role-Based Access
* **Admin:** สามารถจัดการข้อมูลและดูสถิติทั้งหมดได้.
* **User:** สามารถใช้งานการทำนายและค้นหาใบหน้าที่คล้ายกันได้.
