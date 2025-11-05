import io, uuid, mimetypes
from datetime import timedelta
from minio import Minio
from minio.error import S3Error
from ..settings import settings

def _client() -> Minio:
    return Minio(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )

def ensure_bucket():
    c = _client()
    if not c.bucket_exists(settings.MINIO_BUCKET):
        c.make_bucket(settings.MINIO_BUCKET)

def object_key(application_id: str, doc_type: str, filename: str) -> str:
    doc_id = str(uuid.uuid4())
    safe_name = filename.replace("/", "_")
    return f"{application_id}/{doc_type}/{doc_id}__{safe_name}", doc_id

def put_file(application_id: str, doc_type: str, filename: str, blob: bytes) -> tuple[str, str]:
    ensure_bucket()
    key, doc_id = object_key(application_id, doc_type, filename)
    c = _client()
    content_type, _ = mimetypes.guess_type(filename)
    c.put_object(
        bucket_name=settings.MINIO_BUCKET,
        object_name=key,
        data=io.BytesIO(blob),
        length=len(blob),
        content_type=content_type or "application/octet-stream",
    )
    return key, doc_id

def presign_get(key: str, ttl_seconds: int = 3600) -> str:
    c = _client()
    return c.presigned_get_object(settings.MINIO_BUCKET, key, expires=timedelta(seconds=ttl_seconds))
