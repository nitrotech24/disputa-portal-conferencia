"""
TESTE: DisputeService
Objetivo: Testar consulta de disputas na API
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.token_service import TokenService
from services.auth_service import AuthService
from services.dispute_service import DisputeService
from utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    logger.info("=" * 80)
    logger.info("TESTANDO DisputeService")
    logger.info("=" * 80)

    # Inicializar serviços
    token_service = TokenService()
    auth_service = AuthService(token_service)
    dispute_service = DisputeService(token_service, auth_service)

    # Configurações
    customer_code = "305S3073SPA"
    dispute_id = "23724918"

    # TESTE 1: Detalhes da disputa
    logger.info("\n[TESTE 1] Consultando detalhes da disputa...")
    details = dispute_service.get_dispute_details(dispute_id, customer_code)

    if details:
        logger.info("✅ Disputa encontrada!")
        logger.info(f"  Invoice: {details.get('invoiceNumber')}")
        logger.info(f"  Valor: {details.get('disputedAmount')} {details.get('currency')}")
        logger.info(f"  Status: {details.get('statusDescription')}")
    else:
        logger.error("❌ Não conseguiu buscar disputa")
        return

    # TESTE 2: Comentários
    logger.info("\n[TESTE 2] Consultando comentários...")
    comments = dispute_service.get_dispute_comments(dispute_id, customer_code)

    if comments is not None:
        logger.info(f"✅ Total de comentários: {len(comments)}")
    else:
        logger.warning("⚠️  Não conseguiu buscar comentários")

    # TESTE 3: Anexos
    logger.info("\n[TESTE 3] Consultando anexos...")
    attachments = dispute_service.get_dispute_attachments(dispute_id, customer_code)

    if attachments is not None:
        logger.info(f"✅ Total de anexos: {len(attachments)}")
    else:
        logger.warning("⚠️  Não conseguiu buscar anexos")

    # RESUMO
    logger.info("\n" + "=" * 80)
    logger.info("RESUMO")
    logger.info("=" * 80)
    logger.info(f"Disputa: {dispute_id}")
    logger.info(f"Customer: {customer_code}")
    logger.info(f"Status: ✅ SUCESSO")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
