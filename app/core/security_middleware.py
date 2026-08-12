"""
Security Middleware สำหรับป้องกัน vulnerability scanning

ป้องกัน 3 ระดับ:
1. บล็อก path อันตราย (.env, path traversal, openapi.json, etc.)
2. Rate limiting - จำกัดจำนวน request ต่อ IP ต่อนาที
3. Auto-ban - บล็อก IP อัตโนมัติถ้าพยายามเข้า path อันตรายเกินกำหนด
"""

import time
import logging
import re
from collections import defaultdict
from typing import Set

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("uvicorn")


# ============================================================
# Configuration
# ============================================================

# จำนวน request สูงสุดต่อ IP ต่อนาที
RATE_LIMIT_PER_MINUTE: int = 60

# จำนวนครั้งที่เข้า path อันตรายก่อนจะถูก ban
SUSPICIOUS_THRESHOLD: int = 5

# ระยะเวลา ban (วินาที) — default 1 ชั่วโมง
BAN_DURATION_SECONDS: int = 3600

# ระยะเวลา rate-limit window (วินาที)
RATE_LIMIT_WINDOW: int = 60


# ============================================================
# Suspicious path patterns
# ============================================================

# Exact paths ที่ต้องบล็อก
BLOCKED_PATHS: Set[str] = {
    "/.env",
    "/.env.local",
    "/.env.production",
    "/.env.staging",
    "/.env.development",
    "/.env.backup",
    "/.env.bak",
    "/.env.old",
    "/.env.save",
    "/.env.example",
    "/.streamlit/secrets.toml",
    "/openapi.json",
    "/swagger.json",
    "/api/config",
    "/api/predict",
    "/wp-admin",
    "/wp-login.php",
    "/admin",
    "/phpmyadmin",
    "/.git/config",
    "/.git/HEAD",
    "/server-status",
    "/server-info",
    "/.htaccess",
    "/.htpasswd",
    "/web.config",
    "/config.json",
    "/config.yaml",
    "/config.yml",
    "/docker-compose.yml",
    "/docker-compose.yaml",
    "/.dockerenv",
    "/Dockerfile",
    "/package.json",
    "/composer.json",
}

# Regex patterns สำหรับ path ที่น่าสงสัย
BLOCKED_PATH_PATTERNS = [
    re.compile(r"/\.env"),                     # ทุก path ที่มี .env
    re.compile(r"/file[=%].*\.env"),            # path traversal ผ่าน file=../.env
    re.compile(r"\.\./"),                       # directory traversal
    re.compile(r"\.\.\%"),                      # encoded directory traversal
    re.compile(r"/\.git(/|$)"),                 # git directory
    re.compile(r"/\.(svn|hg|bzr)(/|$)"),       # version control dirs
    re.compile(r"\.(sql|bak|backup|dump)$"),    # database dumps
    re.compile(r"/wp-(admin|content|includes)"),# wordpress paths
    re.compile(r"/cgi-bin/"),                   # CGI scripts
    re.compile(r"/actuator"),                   # Spring Boot actuator
]


# ============================================================
# In-memory storage (thread-safe enough for async single-process)
# ============================================================

class RateLimitStore:
    """เก็บข้อมูล rate-limit และ ban list ใน memory"""

    def __init__(self):
        # {ip: [timestamp, timestamp, ...]}
        self.request_counts: dict[str, list[float]] = defaultdict(list)
        # {ip: count} — จำนวนครั้งที่เข้า path อันตราย
        self.suspicious_counts: dict[str, int] = defaultdict(int)
        # {ip: ban_until_timestamp}
        self.banned_ips: dict[str, float] = {}
        # ล่าสุดที่ทำ cleanup
        self._last_cleanup: float = time.time()

    def cleanup(self):
        """ลบข้อมูลเก่าเป็นระยะ ป้องกัน memory leak"""
        now = time.time()
        # cleanup ทุก 5 นาที
        if now - self._last_cleanup < 300:
            return
        self._last_cleanup = now

        # ลบ request counts เก่ากว่า window
        cutoff = now - RATE_LIMIT_WINDOW
        for ip in list(self.request_counts.keys()):
            self.request_counts[ip] = [
                t for t in self.request_counts[ip] if t > cutoff
            ]
            if not self.request_counts[ip]:
                del self.request_counts[ip]

        # ลบ IP ที่ ban หมดอายุ
        for ip in list(self.banned_ips.keys()):
            if self.banned_ips[ip] <= now:
                del self.banned_ips[ip]
                self.suspicious_counts.pop(ip, None)

    def is_banned(self, ip: str) -> bool:
        """ตรวจว่า IP ถูก ban หรือไม่"""
        if ip in self.banned_ips:
            if self.banned_ips[ip] > time.time():
                return True
            else:
                # ban หมดอายุแล้ว
                del self.banned_ips[ip]
                self.suspicious_counts.pop(ip, None)
        return False

    def ban_ip(self, ip: str):
        """แบน IP"""
        self.banned_ips[ip] = time.time() + BAN_DURATION_SECONDS
        logger.warning(
            f"🚫 BANNED IP: {ip} for {BAN_DURATION_SECONDS}s "
            f"(suspicious requests: {self.suspicious_counts[ip]})"
        )

    def record_suspicious(self, ip: str) -> bool:
        """บันทึก request ที่น่าสงสัย, return True ถ้าถึง threshold แล้ว ban"""
        self.suspicious_counts[ip] += 1
        if self.suspicious_counts[ip] >= SUSPICIOUS_THRESHOLD:
            self.ban_ip(ip)
            return True
        return False

    def check_rate_limit(self, ip: str) -> bool:
        """ตรวจ rate limit, return True ถ้าเกิน limit"""
        now = time.time()
        cutoff = now - RATE_LIMIT_WINDOW

        # ลบ timestamps เก่า
        self.request_counts[ip] = [
            t for t in self.request_counts[ip] if t > cutoff
        ]

        if len(self.request_counts[ip]) >= RATE_LIMIT_PER_MINUTE:
            return True  # เกิน limit

        self.request_counts[ip].append(now)
        return False


# Singleton store
_store = RateLimitStore()


# ============================================================
# Helper functions
# ============================================================

def is_suspicious_path(path: str) -> bool:
    """ตรวจว่า path เป็น path ที่น่าสงสัยหรือไม่"""
    # เช็ค decoded path ด้วย
    path_lower = path.lower()

    if path_lower in BLOCKED_PATHS:
        return True

    for pattern in BLOCKED_PATH_PATTERNS:
        if pattern.search(path_lower):
            return True

    return False


# ============================================================
# Middleware
# ============================================================

class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Security Middleware ที่ทำงาน 3 ขั้นตอน:
    1. ตรวจว่า IP ถูก ban หรือไม่
    2. ตรวจว่า path เป็น path อันตรายหรือไม่
    3. ตรวจ rate limit
    """

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path

        # ทำ cleanup เป็นระยะ
        _store.cleanup()

        # ---- ขั้นที่ 1: ตรวจ ban list ----
        if _store.is_banned(client_ip):
            logger.warning(
                f"⛔ BLOCKED banned IP: {client_ip} | Path: {path}"
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied"},
            )

        # ---- ขั้นที่ 2: ตรวจ suspicious path ----
        if is_suspicious_path(path):
            was_banned = _store.record_suspicious(client_ip)
            logger.warning(
                f"🔍 Suspicious request from {client_ip} | Path: {path} | "
                f"Count: {_store.suspicious_counts[client_ip]}/{SUSPICIOUS_THRESHOLD}"
                f"{' → BANNED!' if was_banned else ''}"
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied"},
            )

        # ---- ขั้นที่ 3: ตรวจ rate limit ----
        if _store.check_rate_limit(client_ip):
            logger.warning(
                f"⏱️ Rate limit exceeded for IP: {client_ip} | Path: {path}"
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
            )

        return await call_next(request)
