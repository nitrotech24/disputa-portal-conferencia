"""
atualizar_disputas.py
Atualiza disputas de uma invoice específica na API da Hapag.
"""

import logging
from api_hapag.token_utils import get_valid_token
from api_hapag.consulta_invoice import consultar_invoice
from api_hapag.repos.disputa_repo import upsert_disputa
from api_hapag.repos.invoice_repo import get_invoice_by_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def atualizar_disputas(invoice_id: int) -> None:
    """
    Atualiza disputas de uma invoice específica.
    1. Garante token válido
    2. Consulta disputas da invoice na API
    3. Atualiza tabela de disputas no DB
    """
    logging.info(f"➡️ Atualizando disputas da invoice id={invoice_id}")

    # busca invoice no banco
    invoice = get_invoice_by_id(invoice_id)
    if not invoice:
        logging.error(f"❌ Invoice id={invoice_id} não encontrada no DB.")
        return

    # consulta disputas na API
    disputes = consultar_invoice(invoice.numero_invoice)
    if not disputes:
        logging.info("   ❌ Nenhuma disputa encontrada na API.")
        return

    # salva/atualiza disputas no banco
    for d in disputes:
        dispute_no = d.get("disputeNumber")
        status = d.get("status")

        saved_id = upsert_disputa(invoice_id=invoice.id, dispute_number=dispute_no, status=status)
        logging.info(f"   💾 Disputa {dispute_no} atualizada (id={saved_id}, status={status})")

    logging.info(f"✅ Invoice id={invoice_id} sincronizada com sucesso!")
