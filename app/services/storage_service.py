import aioboto3
from app.core.config import settings


class StorageService:
    def __init__(self):
        self.session = aioboto3.Session()
        self.endpoint_url = f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com"

    async def upload_file(self, file_content: bytes, file_name: str, content_type: str):
        async with self.session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=settings.R2_ACCESS_KEY,
            aws_secret_access_key=settings.R2_SECRET_KEY,
            region_name="auto",
        ) as s3:
            await s3.put_object(
                Bucket=settings.R2_BUCKET_NAME,
                Key=file_name,
                Body=file_content,
                ContentType=content_type,
            )
            return f"{settings.R2_PUBLIC_URL}/{file_name}"


storage_service = StorageService()
