"""
TESTE: AuthService
Objetivo: Testar renovação de tokens via Selenium
ATENÇÃO: Este teste abre o navegador e faz login real!
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.token_service import TokenService
from services.auth_service import AuthService
from utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    logger.info("=" * 80)
    logger.info("TESTANDO AuthService - RENOVAÇÃO DE TOKENS")
    logger.info("=" * 80)
    logger.info("\nATENÇÃO: Este teste vai abrir o navegador e fazer login!")
    logger.info("Pressione Ctrl+C para cancelar nos próximos 5 segundos...")

    import time
    time.sleep(5)

    # Inicializar serviços
    token_service = TokenService()
    auth_service = AuthService(token_service)

    # Renovar todos os tokens
    logger.info("\nIniciando renovação de todos os tokens...")
    all_tokens = auth_service.refresh_all_tokens()

    if all_tokens:
        logger.info("\n" + "=" * 80)
        logger.info("TOKENS RENOVADOS COM SUCESSO")
        logger.info("=" * 80)

        for code, data in all_tokens.items():
            logger.info(f"{data['name'][:50]:50} | {code}")

        logger.info("=" * 80)
        logger.info(f"Total: {len(all_tokens)} tokens")
        logger.info("=" * 80)
    else:
        logger.error("\nFalha ao renovar tokens!")


if __name__ == "__main__":
    main()