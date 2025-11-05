import os
from dotenv import load_dotenv

load_dotenv()

DOCS_BASE_URL = os.getenv("DOCS_BASE_URL", "http://localhost:8001")
EV_BASE_URL   = os.getenv("EV_BASE_URL",   "http://localhost:8002")
ORCH_BASE_URL = os.getenv("ORCH_BASE_URL", "http://localhost:8003")

HTTP_TIMEOUT_S = 60
