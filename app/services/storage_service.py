import aioboto3
from app.core.config import settings


class StorageService:
    def __init__(self):
        self.session = aioboto3.Session()
        self.endpoint_url = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str,
        folder: str = "predictions",
    ):
        full_path = f"{folder}/{file_name}"

        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=settings.R2_ACCESS_KEY,
            aws_secret_access_key=settings.R2_SECRET_KEY,
            region_name="auto",
        ) as s3:
            await s3.put_object(
                Bucket=settings.R2_BUCKET_NAME,
                Key=full_path,
                Body=file_content,
                ContentType=content_type,
            )

            return f"{settings.R2_PUBLIC_URL}/{full_path}"

    async def delete_file(self, file_url_or_key: str):
        """
        ฟังก์ชันสำหรับลบไฟล์ออกจาก Cloudflare R2
        รองรับทั้งการส่ง Path ตรงๆ (เช่น 'predictions/image.jpg')
        และการส่ง Full URL (เช่น 'https://your-public-url.com/predictions/image.jpg')
        """

        if file_url_or_key.startswith(settings.R2_PUBLIC_URL):
            file_key = file_url_or_key.replace(f"{settings.R2_PUBLIC_URL}/", "")
        else:
            file_key = file_url_or_key

        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=settings.R2_ACCESS_KEY,
            aws_secret_access_key=settings.R2_SECRET_KEY,
            region_name="auto",
        ) as s3:
            await s3.delete_object(
                Bucket=settings.R2_BUCKET_NAME,
                Key=file_key,
            )
            print(f"Deleted file successfully: {file_key}")


storage_service = StorageService()
