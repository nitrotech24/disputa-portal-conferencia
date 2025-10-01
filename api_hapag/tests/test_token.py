"""
test_token.py
Testa validação e renovação de tokens
"""

import sys
sys.path.insert(0, '..')

from api_hapag.services.token_service import get_valid_token
from api_hapag.utils.logger import setup_logger

logger = setup_logger()

def main():
    logger.info("Testando token...")

    token = get_valid_token()

    if token:
        logger.info("Token válido obtido")
        logger.info(f"Token (primeiros 50 chars): {token[:50]}...")
    else:
        logger.error("Falha ao obter token válido")

if __name__ == "__main__":
    main()
