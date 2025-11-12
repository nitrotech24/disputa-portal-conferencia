"""
Teste de automação da disputa no portal Maersk.
Executa o fluxo completo até abrir o formulário de disputa.
"""

import time
import logging
from api_maersk.services.dispute_creation_service import MaerskDisputeAutomation
from api_maersk.services.token_service import TokenService

# Configura o logger no mesmo formato usado no restante do projeto
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s"
)
logger = logging.getLogger(__name__)

# Dados de teste
INVOICE_NUMBER = "7539273935"
CUSTOMER_CODE = "305S3073SPA"

CHARGES_TO_DISPUTE = "Charge1, Charge2"
REASON_DESCRIPTION = "Valores incorretos na fatura."
CONTACT_NAME = "Henrique Spencer"
CONTACT_EMAIL = "henrique.spencer@empresa.com"
CONTACT_PHONE = "+55 84 99999-9999"

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("TESTE: CRIAÇÃO DE DISPUTA VIA AUTOMAÇÃO WEB")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Este teste vai:")
    logger.info("1. Abrir o navegador Chrome")
    logger.info("2. Realizar login automático")
    logger.info("3. Buscar a invoice informada")
    logger.info("4. Clicar em 'Contestar' e abrir o formulário de disputa")
    logger.info("")
    logger.info("Pré-requisitos:")
    logger.info("- Conta com acesso à fatura informada")
    logger.info("- Fechar outras sessões ativas do portal Maersk")
    logger.info("")
    logger.info("Pressione Ctrl+C nos próximos 5 segundos para cancelar...")
    logger.info("=" * 80)

    time.sleep(5)

    logger.info("=" * 80)
    logger.info("Iniciando execução")
    logger.info("=" * 80)

    token_service = TokenService()
    automation = MaerskDisputeAutomation(token_service)

    result = automation.create_dispute(
        customer_code=CUSTOMER_CODE,
        invoice_number=INVOICE_NUMBER,
        charges_to_dispute=CHARGES_TO_DISPUTE,
        reason_description=REASON_DESCRIPTION,
        contact_name=CONTACT_NAME,
        contact_email=CONTACT_EMAIL,
        contact_phone=CONTACT_PHONE,
    )

    logger.info("")
    logger.info("=" * 80)
    logger.info("RESULTADO FINAL")
    logger.info("=" * 80)

    if result.get("success"):
        logger.info("Sucesso!")
        logger.info("Mensagem: %s", result.get("message", ""))
    else:
        logger.error("Falha na execução")
        logger.error("Erro: %s", result.get("error", ""))

    logger.info("=" * 80)