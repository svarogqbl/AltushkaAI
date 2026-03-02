import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Адреса сервисов
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
SEARXNG_URL = "http://localhost:8080/search"

# Настройки памяти
MAX_HISTORY_MESSAGES = 35
SUMMARY_THRESHOLD = 40
KEEP_RECENT_MESSAGES = 20
MAX_SUMMARIES_COUNT = 3

# Путь к базе данных
DB_PATH = "altushka_memory.db"

# Настройки поиска
SEARCH_MAX_RESULTS = 4
SEARCH_TIMEOUT = 10

# Пути
BASE_DIR = Path(__file__).parent
HISTORY_DIR = BASE_DIR / "user_histories"
HISTORY_DIR.mkdir(exist_ok=True)