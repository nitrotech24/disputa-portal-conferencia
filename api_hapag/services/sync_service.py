"""
sync_service.py - VERSÃO OTIMIZADA V2
Sincroniza invoices do DB com disputas da API Hapag
CORREÇÃO: API retorna todas as disputas, não por invoice individual
SOLUÇÃO: Buscar todas de uma vez e distribuir por invoice
"""

import logging
import requests
from typing import Optional, Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from api_hapag.repos.invoice_repository import list_invoices
from api_hapag.repos.dispute_repository import (
    upsert_disputa,
    get_disputas_para_atualizar,
    STATUS_FINAIS
)
from api_hapag.utils.storage import load_token
from api_hapag.config.db import get_conn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def buscar_todas_disputas_api() -> List[dict] | None:
    """
    Busca TODAS as disputas de uma vez da API.
    Muito mais eficiente que consultar por invoice individual.
    """
    token = load_token()
    if not token:
        logging.error("Token não encontrado")
        return None

    url = "https://dispute-overview.api.hlag.cloud/api/disputes"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-token": token,
        "Accept": "application/json"
    }

    try:
        logging.info("Buscando TODAS as disputas da API...")
        r = requests.get(url, headers=headers, timeout=30)

        if r.status_code == 200:
            data = r.json()

            # API pode retornar lista ou objeto
            if isinstance(data, dict):
                disputas = [data]
            else:
                disputas = data

            logging.info(f"Total de {len(disputas)} disputas retornadas da API")
            return disputas
        else:
            logging.error(f"Erro {r.status_code}: {r.text}")
            return None

    except requests.RequestException as e:
        logging.error(f"Erro na requisição: {e}")
        return None


def agrupar_disputas_por_invoice(disputas: List[dict]) -> Dict[str, List[dict]]:
    """
    Agrupa disputas pelo número da invoice.
    Retorna dict: {invoice_number: [lista de disputas]}
    """
    grupos = {}

    for disputa in disputas:
        invoice_number = str(disputa.get('invoiceNumber', '')).strip()

        if not invoice_number:
            continue

        if invoice_number not in grupos:
            grupos[invoice_number] = []

        grupos[invoice_number].append(disputa)

    return grupos


def normalizar_disputa(disputa: dict) -> dict:
    """
    Normaliza campos da disputa para o formato esperado pelo banco.
    """
    return {
        'disputeNumber': disputa.get('disputeNumber'),
        'status': disputa.get('status') or disputa.get('disputeStatus') or disputa.get('currentStatus'),
        'dispute_reason': disputa.get('dispute_reason') or disputa.get('disputeReason'),
        'amount': disputa.get('amount') or disputa.get('disputedAmount'),
        'currency': disputa.get('currency'),
        'ref': disputa.get('ref') or disputa.get('reference'),
        'allowSecondReview': disputa.get('allowSecondReview'),
        'disputeCreated': disputa.get('disputeCreated') or disputa.get('createdDate'),
        'invoiceNumber': disputa.get('invoiceNumber')
    }


def sincronizar_disputas(limit: Optional[int] = None, max_workers: int = 10, modo: str = "inteligente"):
    """
    Sincronização de disputas OTIMIZADA.
    Busca todas as disputas de UMA vez ao invés de consultar invoice por invoice.

    Args:
        limit: Número de invoices a processar (None = todas relevantes)
        max_workers: Não usado nesta versão (mantido para compatibilidade)
        modo: "completo" | "inteligente" | "recentes" (não faz diferença nesta versão)
    """

    logging.info("=" * 60)
    logging.info("SINCRONIZAÇÃO DE DISPUTAS - MODO OTIMIZADO")
    logging.info("=" * 60)

    # 1. Busca TODAS as disputas de uma vez
    todas_disputas = buscar_todas_disputas_api()

    if not todas_disputas:
        logging.error("Não foi possível buscar disputas da API")
        return

    # 2. Agrupa por invoice
    logging.info("Agrupando disputas por invoice...")
    disputas_por_invoice = agrupar_disputas_por_invoice(todas_disputas)

    logging.info(f"Total de {len(disputas_por_invoice)} invoices têm disputas")
    logging.info("")

    # 3. Busca invoices do banco para fazer match
    logging.info("Carregando invoices do banco...")
    todas_invoices = list_invoices(limit=None)

    # Cria mapeamento: numero_invoice -> invoice_id
    invoice_map = {inv.numero_invoice: inv.id for inv in todas_invoices}

    # 4. Processa disputas
    invoices_processadas = 0
    disputas_salvas = 0
    disputas_ignoradas = 0
    invoices_nao_encontradas = []

    for invoice_number, disputas in disputas_por_invoice.items():
        # Verifica se invoice existe no banco
        invoice_id = invoice_map.get(invoice_number)

        if not invoice_id:
            invoices_nao_encontradas.append(invoice_number)
            disputas_ignoradas += len(disputas)
            continue

        invoices_processadas += 1
        logging.info(
            f"[{invoices_processadas}/{len(disputas_por_invoice)}] Invoice {invoice_number}: {len(disputas)} disputa(s)")

        for disputa in disputas:
            dispute_no = disputa.get('disputeNumber')
            status = disputa.get('status')

            if not status:
                logging.warning(f"  Disputa {dispute_no} sem status, ignorando")
                continue

            try:
                # Normaliza disputa
                disputa_normalizada = normalizar_disputa(disputa)

                saved_id = upsert_disputa(
                    invoice_id=invoice_id,
                    dispute_number=dispute_no,
                    data=disputa_normalizada
                )

                disputas_salvas += 1
                logging.info(f"  Disputa {dispute_no} sincronizada (status={status}, id={saved_id})")

            except Exception as e:
                logging.error(f"  Erro ao salvar disputa {dispute_no}: {e}")

    # Resumo
    logging.info("")
    logging.info("=" * 60)
    logging.info("Sincronização concluída:")
    logging.info(f"  - {len(todas_disputas)} disputas na API")
    logging.info(f"  - {len(disputas_por_invoice)} invoices com disputas")
    logging.info(f"  - {invoices_processadas} invoices processadas")
    logging.info(f"  - {disputas_salvas} disputas sincronizadas")

    if disputas_ignoradas > 0:
        logging.info(f"  - {disputas_ignoradas} disputas ignoradas (invoice não existe no banco)")

    if invoices_nao_encontradas:
        logging.warning(f"  - {len(invoices_nao_encontradas)} invoices com disputa não estão no banco:")
        for inv in invoices_nao_encontradas[:10]:
            logging.warning(f"      {inv}")
        if len(invoices_nao_encontradas) > 10:
            logging.warning(f"      ... e mais {len(invoices_nao_encontradas) - 10}")

    logging.info("=" * 60)


def atualizar_disputas_antigas(max_workers: int = 5):
    """
    Atualiza apenas disputas que precisam de refresh COM PARALELIZAÇÃO.

    Args:
        max_workers: Número de threads simultâneas (padrão: 5)
    """
    logging.info("Buscando disputas desatualizadas...")

    disputas = get_disputas_para_atualizar()
    total = len(disputas)

    if total == 0:
        logging.info("Nenhuma disputa precisa ser atualizada")
        return

    logging.info(f"Total de {total} disputas precisam ser atualizadas")
    logging.info(f"  (Status finais ignorados: {', '.join(STATUS_FINAIS)})")
    logging.info(f"Processando com {max_workers} threads paralelas...")
    logging.info("")

    atualizadas = 0
    erros = 0

    def processar_disputa(disp, idx):
        """Atualiza uma disputa individual consultando a API"""
        from api_hapag.services.dispute_service import atualizar_status_disputa

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
    logging.info("Atualização concluída:")
    logging.info(f"  - {total} disputas processadas")
    logging.info(f"  - {atualizadas} atualizadas com sucesso")
    if erros > 0:
        logging.info(f"  - {erros} erros")
    logging.info("=" * 60)