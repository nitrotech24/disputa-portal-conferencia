"""
settings.py
Configurações centralizadas da API Hapag
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Credenciais
HAPAG_USERNAME = os.getenv("HL_USER")
HAPAG_PASSWORD = os.getenv("HL_PASS")

if not HAPAG_USERNAME or not HAPAG_PASSWORD:
    raise ValueError("Credenciais não configuradas no .env")

# URLs
HAPAG_LOGIN_URL = "https://www.hapag-lloyd.com/solutions/invoice-overview"
HAPAG_DISPUTE_URL = "https://www.hapag-lloyd.com/solutions/dispute-overview/#/?language=pt"
HAPAG_API_BASE_URL = "https://dispute-overview.api.hlag.cloud/api"

# Banco de Dados
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASS", "")
DB_NAME = os.getenv("DB_NAME", "feat_pc")

# Selenium
SELENIUM_TIMEOUT = 20
SELENIUM_WAIT_AFTER_LOGIN = 10

# Paths
ARTIFACTS_DIR = "artifacts"
COOKIES_FILE = f"{ARTIFACTS_DIR}/cookies.json"
TOKEN_FILE = f"{ARTIFACTS_DIR}/xtoken.txt"
