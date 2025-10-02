"""
sync_service.py
Sincroniza invoices do DB com disputas da API Hapag.
"""

import logging
from typing import Optional
from api_hapag.repos.invoice_repository import list_invoices
from api_hapag.repos.dispute_repository import upsert_disputa
from api_hapag.services.dispute_service import consultar_invoice

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def sincronizar_disputas(limit: Optional[int] = None):
    """
    Pega invoices do banco, consulta disputas na API da Hapag
    e salva no DB (insert/update).
    
    Args:
        limit: Numero de invoices a processar (None = todas)
    """
    invoices = list_invoices(limit=limit)
    total = len(invoices)
    
    if limit is None:
        logging.info(f"{total} invoices carregadas do banco (TODAS)")
    else:
        logging.info(f"{total} invoices carregadas do banco (limit={limit})")

    for inv in invoices:
        logging.info(f"Verificando invoice {inv.numero_invoice} (id={inv.id})")

        disputes = consultar_invoice(inv.numero_invoice)

        if not disputes:
            logging.info("   Nenhuma disputa encontrada na API")
            continue

        for d in disputes:
            dispute_no = d.get("disputeNumber")
            status = d.get("status")

            logging.info(f"   Disputa {dispute_no} encontrada (status={status})")

            saved_id = upsert_disputa(
                invoice_id=inv.id,
                dispute_number=dispute_no,
                status=status
            )
            logging.info(
                f"   Disputa {dispute_no} sincronizada no banco "
                f"(id={saved_id}, status={status})"
            )