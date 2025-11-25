"""
Teste de automação da disputa no portal Maersk.
Executa o fluxo completo até abrir o formulário de disputa.
"""

import time
import logging
from api_maersk.services.dispute_creation_service import MaerskDisputeAutomation
from api_maersk.services.token_service import TokenService
from api_maersk.services.auth_service import AuthService

# Configura o logger no mesmo formato usado no restante do projeto
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] - %(message)s"
)
logger = logging.getLogger(__name__)

# Dados de teste
INVOICE_NUMBER = "7539273935"
CUSTOMER_CODE = "305S3073SPA"

# Configurações para criação via API
DISPUTE_REASON_CODE = "0001"  # 0001 = Incorrect rates
DISPUTE_REASON_DESCRIPTION = "Incorrect rates"
NOTE_DESCRIPTION = "TESTE - Disputa criada via automação API"
CONTACT_NAME = "Fernando"
CONTACT_EMAIL = "fernando.conceicao@nitro.com.br"
CONTACT_PHONE = "5511999999999"

# Charges customizados (opcional - se None, busca automaticamente da invoice)
# Exemplo de como especificar charges manualmente:
CUSTOM_CHARGES = [
    {
        "billing_item_no": "00000001",
        "charge_name": "Detention Fee - Export (DTS)",
        "current_amount": "1500.0",
        "currency": "USD",
        "expected_amount": "1500",  # Valor que deveria ser
        "dispute_category": "rateNotAsPerContractualAgreement"
    }
]

# IMPORTANTE: Dry run por padrao para nao criar disputa real
DRY_RUN = True  # Mude para False APENAS se quiser criar disputa de verdade

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("TESTE: CRIACAO DE DISPUTA VIA API")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Este teste vai:")
    logger.info("1. Obter token valido para o customer")
    logger.info("2. Buscar informacoes da invoice")
    logger.info("3. Montar payload de disputa")

    if DRY_RUN:
        logger.info("4. [DRY RUN] Mostrar payload sem enviar")
        logger.warning("MODO DRY RUN ATIVADO - Disputa NAO sera criada de verdade!")
    else:
        logger.info("4. [REAL] Enviar requisicao para criar disputa")
        logger.warning("MODO REAL - Disputa SERA CRIADA de verdade!")

    logger.info("")
    logger.info("Configuracoes:")
    logger.info(f"- Customer: {CUSTOMER_CODE}")
    logger.info(f"- Invoice: {INVOICE_NUMBER}")
    logger.info(f"- Dry Run: {DRY_RUN}")
    logger.info("")

    if not DRY_RUN:
        logger.warning("ATENCAO: Voce esta prestes a criar uma disputa REAL!")
        logger.warning("Nao ha como desfazer esta acao!")
        logger.info("Pressione Ctrl+C nos proximos 10 segundos para cancelar...")
        time.sleep(10)
    else:
        logger.info("Pressione Ctrl+C nos proximos 3 segundos para cancelar...")
        time.sleep(3)

    logger.info("=" * 60)
    logger.info("Iniciando execucao")
    logger.info("=" * 60)

    # Inicializar serviços
    token_service = TokenService()
    auth_service = AuthService(token_service)
    automation = MaerskDisputeAutomation(token_service, auth_service)

    # Criar disputa via API
    result = automation.create_dispute_api(
        customer_code=CUSTOMER_CODE,
        invoice_number=INVOICE_NUMBER,
        dispute_reason_code=DISPUTE_REASON_CODE,
        dispute_reason_description=DISPUTE_REASON_DESCRIPTION,
        note_description=NOTE_DESCRIPTION,
        contact_name=CONTACT_NAME,
        contact_email=CONTACT_EMAIL,
        contact_phone=CONTACT_PHONE,
        charges=CUSTOM_CHARGES,  # Ou None para buscar automaticamente
        dry_run=DRY_RUN
    )

    logger.info("")
    logger.info("=" * 60)
    logger.info("RESULTADO FINAL")
    logger.info("=" * 60)

    if result.get("success"):
        logger.info("Sucesso!")
        logger.info(f"Mensagem: {result.get('message', '')}")

        if result.get("dry_run"):
            logger.info("\nPayload que seria enviado:")
            import json
            logger.info(json.dumps(result.get("payload", {}), indent=2, ensure_ascii=False))
        elif result.get("dispute_id"):
            logger.info(f"ID da disputa criada: {result.get('dispute_id')}")
    else:
        logger.error("Falha na execucao")
        logger.error(f"Erro: {result.get('error', '')}")
        logger.error(f"Mensagem: {result.get('message', '')}")

    logger.info("=" * 60)