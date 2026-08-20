import aioboto3
from app.core.config import settings


class StorageService:
    """
    จัดการอัปโหลดและลบไฟล์บน Cloudflare R2 Object Storage
    """

    def __init__(self):
        """
        กำหนด aioboto3 Session และ Endpoint URL ของ Cloudflare R2
        """
        self.session = aioboto3.Session()
        self.endpoint_url = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
        self._s3_client = None

    async def _get_client(self):
        """
        สร้าง S3-compatible Client สำหรับเชื่อมต่อ Cloudflare R2
        """
        return self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=settings.R2_ACCESS_KEY,
            aws_secret_access_key=settings.R2_SECRET_KEY,
            region_name="auto",
        )

    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str,
        folder: str = "predictions",
    ):
        """
        อัปโหลดไฟล์ไปยัง Cloudflare R2 และ Return Public URL
        """
        full_path = f"{folder}/{file_name}"

        client = await self._get_client()
        async with client as s3:
            await s3.put_object(
                Bucket=settings.R2_BUCKET_NAME,
                Key=full_path,
                Body=file_content,
                ContentType=content_type,
            )

            return f"{settings.R2_PUBLIC_URL}/{full_path}"

    async def delete_file(self, file_url_or_key: str):
        """
        ลบไฟล์ออกจาก Cloudflare R2 โดยรับได้ทั้ง Public URL และ File Key
        """
        if file_url_or_key.startswith(settings.R2_PUBLIC_URL):
            file_key = file_url_or_key.replace(f"{settings.R2_PUBLIC_URL}/", "")
        else:
            file_key = file_url_or_key

        client = await self._get_client()
        async with client as s3:
            await s3.delete_object(
                Bucket=settings.R2_BUCKET_NAME,
                Key=file_key,
            )
            print(f"Deleted file successfully: {file_key}")


storage_service = StorageService()
