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
import ipaddress
from collections import defaultdict
from typing import Set

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("uvicorn")


def is_private_ip(ip_str: str) -> bool:
    """ตรวจว่า IP เป็น Private IP, Loopback หรือ Local Proxy หรือไม่"""
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


def get_client_ip(request: Request) -> str:
    """
    ดึง IP จริงของ Client จาก Headers (รองรับ Reverse Proxy เช่น Hugging Face, Cloudflare)
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client = forwarded_for.split(",")[0].strip()
        if client:
            return client

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()

    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip:
        return cf_ip.strip()

    return request.client.host if request.client else "unknown"


RATE_LIMIT_PER_MINUTE: int = 60
SUSPICIOUS_THRESHOLD: int = 5
BAN_DURATION_SECONDS: int = 3600
RATE_LIMIT_WINDOW: int = 60


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

BLOCKED_PATH_PATTERNS = [
    re.compile(r"/\.env"),
    re.compile(r"/file[=%].*\.env"),
    re.compile(r"\.\./"),
    re.compile(r"\.\.\%"),
    re.compile(r"/\.git(/|$)"),
    re.compile(r"/\.(svn|hg|bzr)(/|$)"),
    re.compile(r"\.(sql|bak|backup|dump)$"),
    re.compile(r"/wp-(admin|content|includes)"),
    re.compile(r"/cgi-bin/"),
    re.compile(r"/actuator"),
]


class RateLimitStore:
    """เก็บข้อมูล rate-limit และ ban list ใน memory"""

    def __init__(self):
        self.request_counts: dict[str, list[float]] = defaultdict(list)
        self.suspicious_counts: dict[str, int] = defaultdict(int)
        self.banned_ips: dict[str, float] = {}
        self._last_cleanup: float = time.time()

    def cleanup(self):
        """ลบข้อมูลเก่าเป็นระยะ ป้องกัน memory leak"""
        now = time.time()
        if now - self._last_cleanup < 300:
            return
        self._last_cleanup = now

        cutoff = now - RATE_LIMIT_WINDOW
        for ip in list(self.request_counts.keys()):
            self.request_counts[ip] = [
                t for t in self.request_counts[ip] if t > cutoff
            ]
            if not self.request_counts[ip]:
                del self.request_counts[ip]

        for ip in list(self.banned_ips.keys()):
            if self.banned_ips[ip] <= now:
                del self.banned_ips[ip]
                self.suspicious_counts.pop(ip, None)

    def is_banned(self, ip: str) -> bool:
        """ตรวจว่า IP ถูก ban หรือไม่ (ไม่แบน Private/Proxy IP)"""
        if is_private_ip(ip):
            return False

        if ip in self.banned_ips:
            if self.banned_ips[ip] > time.time():
                return True
            else:
                del self.banned_ips[ip]
                self.suspicious_counts.pop(ip, None)
        return False

    def ban_ip(self, ip: str):
        """แบน IP (ยกเว้น Private/Proxy IP)"""
        if is_private_ip(ip):
            logger.info(f"Skipped banning private/proxy IP: {ip}")
            return

        self.banned_ips[ip] = time.time() + BAN_DURATION_SECONDS
        logger.warning(
            f"BANNED IP: {ip} for {BAN_DURATION_SECONDS}s "
            f"(suspicious requests: {self.suspicious_counts[ip]})"
        )

    def record_suspicious(self, ip: str) -> bool:
        """บันทึก request ที่น่าสงสัย, return True ถ้าถึง threshold แล้ว ban"""
        if is_private_ip(ip):
            return False

        self.suspicious_counts[ip] += 1
        if self.suspicious_counts[ip] >= SUSPICIOUS_THRESHOLD:
            self.ban_ip(ip)
            return True
        return False

    def check_rate_limit(self, ip: str) -> bool:
        """ตรวจ rate limit, return True ถ้าเกิน limit (ยกเว้น Private IP)"""
        if is_private_ip(ip):
            return False

        now = time.time()
        cutoff = now - RATE_LIMIT_WINDOW

        self.request_counts[ip] = [
            t for t in self.request_counts[ip] if t > cutoff
        ]

        if len(self.request_counts[ip]) >= RATE_LIMIT_PER_MINUTE:
            return True

        self.request_counts[ip].append(now)
        return False


_store = RateLimitStore()


def is_suspicious_path(path: str) -> bool:
    """ตรวจว่า path เป็น path ที่น่าสงสัยหรือไม่"""
    path_lower = path.lower()

    if path_lower in BLOCKED_PATHS:
        return True

    for pattern in BLOCKED_PATH_PATTERNS:
        if pattern.search(path_lower):
            return True

    return False


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Security Middleware ที่ทำงาน 3 ขั้นตอน:
    1. ตรวจว่า IP ถูก ban หรือไม่
    2. ตรวจว่า path เป็น path อันตรายหรือไม่
    3. ตรวจ rate limit
    """

    async def dispatch(self, request: Request, call_next):
        client_ip = get_client_ip(request)
        path = request.url.path

        _store.cleanup()

        if _store.is_banned(client_ip):
            logger.warning(
                f"BLOCKED banned IP: {client_ip} | Path: {path}"
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied"},
            )

        if is_suspicious_path(path):
            was_banned = _store.record_suspicious(client_ip)
            logger.warning(
                f"Suspicious request from {client_ip} | Path: {path} | "
                f"Count: {_store.suspicious_counts[client_ip]}/{SUSPICIOUS_THRESHOLD}"
                f"{' -> BANNED!' if was_banned else ''}"
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "Access denied"},
            )

        # ---- ขั้นที่ 3: ตรวจ rate limit ----
        if _store.check_rate_limit(client_ip):
            logger.warning(
                f"Rate limit exceeded for IP: {client_ip} | Path: {path}"
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
            )

        return await call_next(request)

