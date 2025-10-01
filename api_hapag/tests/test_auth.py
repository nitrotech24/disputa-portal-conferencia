"""
test_auth.py
Renova tokens manualmente via Selenium
"""

import sys
sys.path.insert(0, '..')

from api_hapag.services.auth_service import login_and_get_token
from api_hapag.utils.logger import setup_logger

logger = setup_logger()

def main():
    logger.info("Renovando token via Selenium...")

    token = login_and_get_token()

    if token:
        logger.info("Token renovado com sucesso!")
        logger.info("Token salvo em: artifacts/xtoken.txt")
    else:
        logger.error("Falha ao renovar token")

if __name__ == "__main__":
    main()
