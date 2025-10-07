"""
sync_service.py
Sincroniza invoices do DB com disputas da API Hapag.
VERSÃO COM PROCESSAMENTO PARALELO
"""

import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from api_hapag.repos.invoice_repository import list_invoices
from api_hapag.repos.dispute_repository import (
    upsert_disputa,
    get_disputas_para_atualizar,
    STATUS_FINAIS
)
from api_hapag.services.dispute_service import (
    consultar_invoice,
    atualizar_status_disputa
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def processar_invoice(inv, idx, total):
    """
    Processa uma única invoice (usado pelo ThreadPoolExecutor)
    """
    resultado = {
        'invoice_id': inv.id,
        'invoice_number': inv.numero_invoice,
        'disputas_encontradas': 0,
        'disputas_salvas': 0,
        'erro': None
    }

    try:
        logging.info(f"[{idx}/{total}] Verificando invoice {inv.numero_invoice} (id={inv.id})")

        disputes = consultar_invoice(inv.numero_invoice)

        if not disputes:
            logging.info(f"   ℹ️  Invoice {inv.numero_invoice}: Nenhuma disputa encontrada")
            return resultado

        resultado['disputas_encontradas'] = len(disputes)

        for d in disputes:
            dispute_no = d.get('disputeNumber')
            status = d.get('status')

            logging.info(
                f"   📌 Invoice {inv.numero_invoice}: Disputa {dispute_no} "
                f"(status={status}, valor={d.get('amount')} {d.get('currency')})"
            )

            saved_id = upsert_disputa(
                invoice_id=inv.id,
                dispute_number=dispute_no,
                data=d
            )

            resultado['disputas_salvas'] += 1
            logging.info(f"   ✅ Disputa {dispute_no} sincronizada (id={saved_id})")

    except Exception as e:
        resultado['erro'] = str(e)
        logging.error(f"   ❌ Erro ao processar invoice {inv.numero_invoice}: {e}")

    return resultado


def sincronizar_disputas(limit: Optional[int] = None, max_workers: int = 10):
    """
    Sincronização completa de disputas COM PARALELIZAÇÃO.

    Args:
        limit: Número de invoices a processar (None = todas)
        max_workers: Número de threads simultâneas (padrão: 10)
    """
    invoices = list_invoices(limit=limit)
    total = len(invoices)

    if limit is None:
        logging.info(f"📋 {total} invoices HAPAG carregadas (TODAS)")
    else:
        logging.info(f"📋 {total} invoices HAPAG carregadas (limit={limit})")

    logging.info(f"🚀 Processando com {max_workers} threads paralelas...")
    logging.info("")

    invoices_com_disputa = 0
    total_disputas_salvas = 0
    erros = 0

    # Processa invoices em paralelo
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submete todas as tarefas
        futures = {
            executor.submit(processar_invoice, inv, idx, total): inv
            for idx, inv in enumerate(invoices, 1)
        }

        # Processa resultados conforme vão completando
        for future in as_completed(futures):
            resultado = future.result()

            if resultado['disputas_salvas'] > 0:
                invoices_com_disputa += 1
                total_disputas_salvas += resultado['disputas_salvas']

            if resultado['erro']:
                erros += 1

    # Resumo
    logging.info("")
    logging.info("=" * 60)
    logging.info(f"✅ Sincronização concluída:")
    logging.info(f"   - {total} invoices processadas")
    logging.info(f"   - {invoices_com_disputa} invoices com disputa")
    logging.info(f"   - {total_disputas_salvas} disputas sincronizadas")
    if erros > 0:
        logging.info(f"   - ⚠️  {erros} erros")
    logging.info("=" * 60)


def atualizar_disputas_antigas(max_workers: int = 5):
    """
    Atualiza apenas disputas que precisam de refresh COM PARALELIZAÇÃO.

    Args:
        max_workers: Número de threads simultâneas (padrão: 5)
    """
    logging.info("🔄 Buscando disputas desatualizadas...")

    disputas = get_disputas_para_atualizar()
    total = len(disputas)

    if total == 0:
        logging.info("✅ Nenhuma disputa precisa ser atualizada")
        return

    logging.info(f"📋 {total} disputas precisam ser atualizadas")
    logging.info(f"   (Status finais ignorados: {', '.join(STATUS_FINAIS)})")
    logging.info(f"🚀 Processando com {max_workers} threads paralelas...")
    logging.info("")

    atualizadas = 0
    erros = 0

    def processar_disputa(disp, idx):
        logging.info(
            f"[{idx}/{total}] Atualizando disputa {disp.dispute_number} "
            f"(id={disp.id}, status atual={disp.status})"
        )
        return atualizar_status_disputa(disp.id, disp.dispute_number)

    # Processa disputas em paralelo
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(processar_disputa, disp, idx): disp
            for idx, disp in enumerate(disputas, 1)
        }

        for future in as_completed(futures):
            if future.result():
                atualizadas += 1
            else:
                erros += 1

    # Resumo
    logging.info("")
    logging.info("=" * 60)
    logging.info(f"✅ Atualização concluída:")
    logging.info(f"   - {total} disputas processadas")
    logging.info(f"   - {atualizadas} atualizadas com sucesso")
    if erros > 0:
        logging.info(f"   - ⚠️  {erros} erros")
    logging.info("=" * 60)