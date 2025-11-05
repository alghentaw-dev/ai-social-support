import io, os
from minio import Minio
from ..settings import settings
from .minio_client import client

def fetch_object(object_key: str) -> tuple[bytes, str]:
    c: Minio = client()
    resp = c.get_object(settings.MINIO_BUCKET, object_key)
    data = resp.read()
    resp.close(); resp.release_conn()
    # last path chunk is the filename after "__"
    fname = os.path.basename(object_key).split("__", 1)[-1]
    return data, fname
