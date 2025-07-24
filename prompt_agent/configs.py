import os
from pathlib import Path

from dotenv import load_dotenv

## LLM API
load_dotenv()
API_KEY = os.environ.get("API_KEY")
BASE_URL = os.environ.get("BASE_URL")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL")

OUTPUT_PROMPT_START_TAG = "<prompt>"

OUTPUT_PROMPT_END_TAG = "</prompt>"


## REDIS
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))

## DASHBOARD AUTHENTICATION
DASHBOARD_USERNAME = os.environ.get("DASHBOARD_USERNAME", "admin")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "password123")

# retrival
# 检查所有大写的变量（通常是常量/环境变量）
current_locals = locals().copy()
for var_name, var_value in current_locals.items():
    if var_name.isupper() and not var_name.startswith("_"):
        # 对于数值类型，检查是否为 None 而不是 falsy
        if var_name in ["REDIS_PORT", "REDIS_DB"]:
            assert var_value is not None, f"{var_name} should be set."
        else:
            assert var_value, f"{var_name} should be set."

## VECTOR DB
DEFAULT_VECTOR_DB_NAME = "default"
DEFAULT_RETRIVAL_COUNT = 3
ENABLE_VECTOR_DB_RETRIVAL = False

ROOT = Path(__file__).parent.parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True, parents=True)

DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)

VECTOR_DB_DIR = DATA_DIR / "vector_db"
VECTOR_DB_DIR.mkdir(exist_ok=True, parents=True)


DEFAULT_TOKENIZER = "cl100k_base"
USE_TOKEN_SHORTEN = True


DATA_DIR = ROOT / "data"

DB_PATH = DATA_DIR / "db.sqlite3"
DB_URL = f"sqlite://{DB_PATH}"

POE_OPENAI_LIKE_API_KEY = "sk-poe-api-dfascvu2"

GROK_CLIENT_LIMIT_CHECKS_INTERVAL_MINUTES = 1 * 60

PROXIES = {}

if __name__ == "__main__":
    print(VECTOR_DB_DIR)
