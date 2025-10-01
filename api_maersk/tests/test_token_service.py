"""
TESTE: TokenService
Objetivo: Verificar se conseguimos ler e validar tokens automaticamente
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
    logger.info("TESTANDO TokenService")
    logger.info("=" * 80)

    token_service = TokenService()
    auth_service = AuthService(token_service)

    # TESTE 1: Carregar tokens
    logger.info("\n[TESTE 1] Carregando tokens do arquivo...")
    tokens = token_service.load_tokens()
    if not tokens:
        logger.error("❌ Nenhum token encontrado!")
        return
    logger.info(f"✅ {len(tokens)} tokens carregados\n")

    logger.info("Customers disponíveis:")
    for code, data in tokens.items():
        logger.info(f"  - {code}: {data['name']}")

    # TESTE 2: Pegar token válido automaticamente
    logger.info("\n[TESTE 2] Pegando token válido de 305S3073SPA...")
    customer_code = "305S3073SPA"
    token = token_service.get_valid_token(customer_code, auth_service=auth_service)

    if token:
        logger.info(f"✅ Token válido obtido: {token[:50]}...")
    else:
        logger.error("❌ Não conseguiu obter token válido")

    # TESTE 3: Converter código
    logger.info("\n[TESTE 3] Convertendo código para API...")
    api_code = token_service.get_api_customer_code(customer_code)
    logger.info(f"  Token code: {customer_code}")
    logger.info(f"  API code: {api_code}")

    # RESUMO
    logger.info("\n" + "=" * 80)
    logger.info("RESUMO")
    logger.info("=" * 80)
    logger.info(f"Total de tokens: {len(tokens)}")
    logger.info(f"Token testado: {customer_code}")
    logger.info(f"Status: {'VÁLIDO ✅' if token else 'FALHOU ❌'}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
