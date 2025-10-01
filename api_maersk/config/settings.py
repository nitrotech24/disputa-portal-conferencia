import os
from pathlib import Path
from dotenv import load_dotenv

# Diretórios
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=BASE_DIR.parent / ".env")

# Artifacts
ARTIFACTS_DIR = BASE_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

# Arquivos
TOKENS_FILE = ARTIFACTS_DIR / "maersk_all_tokens.json"

# Credenciais Maersk
MAERSK_USERNAME = os.getenv("MAERSK_USERNAME")
MAERSK_PASSWORD = os.getenv("MAERSK_PASSWORD")

# URLs
MAERSK_BASE_URL = "https://www.maersk.com"
MAERSK_LOGIN_URL = f"{MAERSK_BASE_URL}/portaluser/select-customer"
API_BASE_URL = "https://api.maersk.com"

# API Configs
CONSUMER_KEY = "mWGhMttfQt4mvDiTBqoAfM8Sd0tyiZrj"
CARRIER_CODE = "MAEU"

# Mapeamento de códigos de clientes
CUSTOMER_CODE_MAPPING = {
    "305S3073SPA": "BRS3073SPA",
    "30501112445": "BR01112445",
    "30501348288": "BR01348288",
    "30501348218": "BR01348218",
    "30501113841": "BR01113841",
}

# Selenium
SELENIUM_TIMEOUT = 30
PAGE_LOAD_WAIT = 3
TOKEN_CHECK_INTERVAL = 1
MAX_TOKEN_CHECKS = 20

# --- Configuração do MySQL ---
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")  

# Validação: garante que credenciais críticas estão configuradas
if not DB_PASSWORD:
    raise ValueError(
        "❌ DB_PASSWORD não configurada!\n"
        "   Verifique o arquivo .env na raiz do projeto."
    )

if not DB_HOST or not DB_NAME or not DB_USER:
    raise ValueError(
        "❌ Credenciais do banco incompletas!\n"
        "   Verifique se DB_HOST, DB_NAME e DB_USER estão no .env"
    )