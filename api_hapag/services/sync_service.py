"""
sync_disputas.py
Sincroniza invoices do DB com disputas da API Hapag.
"""

import logging
from api_hapag.repos.invoice_repository import list_invoices
from api_hapag.repos.disputa_repository import upsert_disputa
from api_hapag.services.dispute_service import consultar_invoice  # <- corrigido

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def sincronizar_disputas(limit: int = 10):
    """
    Pega invoices do banco, consulta disputas na API da Hapag
    e salva no DB (insert/update).
    """
    invoices = list_invoices(limit=limit)
    logging.info(f"🔎 {len(invoices)} invoices carregadas do banco.")

    for inv in invoices:
        logging.info(f"➡️ Verificando invoice {inv.numero_invoice} (id={inv.id})")

        # chama API para ver disputas da invoice
        disputes = consultar_invoice(inv.numero_invoice)

        if not disputes:
            logging.info("   ❌ Nenhuma disputa encontrada na API.")
            continue

        for d in disputes:
            dispute_no = d.get("disputeNumber")
            status = d.get("status")

            logging.info(f"   ✅ Disputa {dispute_no} encontrada (status={status})")

            # salva no banco (insere ou atualiza)
            saved_id = upsert_disputa(
                invoice_id=inv.id,
                dispute_number=dispute_no,
                status=status
            )
            logging.info(
                f"   💾 Disputa {dispute_no} sincronizada no banco "
                f"(id={saved_id}, status={status})"
            )
