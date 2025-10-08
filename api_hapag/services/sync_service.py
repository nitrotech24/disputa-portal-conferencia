"""
sync_service.py -
Sincroniza disputas E invoices relacionadas (não todas as invoices)
 Busca disputas primeiro, sincroniza apenas invoices necessárias
"""

import logging
import requests
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
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
        logging.info("Buscando todas as disputas da API...")
        r = requests.get(url, headers=headers, timeout=30)

        if r.status_code == 200:
            data = r.json()

            if isinstance(data, dict):
                disputas = [data]
            else:
                disputas = data

            logging.info(f"Total de {len(disputas)} disputas encontradas")
            return disputas
        else:
            logging.error(f"Erro {r.status_code}: {r.text}")
            return None

    except requests.RequestException as e:
        logging.error(f"Erro na requisição: {e}")
        return None


def buscar_invoice_da_api(invoice_number: str) -> dict | None:
    """
    Busca UMA invoice específica da API Hapag.
    Usado apenas quando a invoice não existe no banco mas tem disputa.
    """
    token = load_token()
    if not token:
        logging.error("Token não encontrado")
        return None

    url = "https://invoice-overview.api.hlag.cloud/api/invoices"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-token": token,
        "Accept": "application/json"
    }

    try:
        r = requests.get(url, headers=headers, timeout=30)

        if r.status_code == 200:
            data = r.json()
            invoices = data.get('invoiceList', [])

            # Procura a invoice específica
            for inv in invoices:
                if str(inv.get('invoiceNumber')) == str(invoice_number):
                    return inv

            logging.warning(f"Invoice {invoice_number} não encontrada na API")
            return None
        else:
            logging.error(f"Erro {r.status_code}: {r.text}")
            return None

    except requests.RequestException as e:
        logging.error(f"Erro na requisição: {e}")
        return None


def inserir_invoice_no_banco(invoice_data: dict) -> int | None:
    """
    Insere uma invoice no banco de dados.
    """
    sql = """
        INSERT INTO invoice (
            numero_invoice, armador, numero_bl, valor, status, 
            created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP(3), CURRENT_TIMESTAMP(3))
    """

    statuses = invoice_data.get('invoiceStatuses', [])
    status = statuses[0] if statuses else 'UNKNOWN'

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (
                str(invoice_data.get('invoiceNumber')),
                'HAPAG',
                str(invoice_data.get('bookingNumber', '')),
                invoice_data.get('invoiceAmount'),
                status
            ))
            conn.commit()
            return cur.lastrowid
    except Exception as e:
        logging.error(f"Erro ao inserir invoice: {e}")
        return None


def atualizar_invoice_no_banco(invoice_id: int, invoice_data: dict) -> bool:
    """
    Atualiza uma invoice existente no banco.
    """
    sql = """
        UPDATE invoice
        SET numero_bl = %s,
            valor = %s,
            status = %s,
            updated_at = CURRENT_TIMESTAMP(3)
        WHERE id = %s AND armador = 'HAPAG'
    """

    statuses = invoice_data.get('invoiceStatuses', [])
    status = statuses[0] if statuses else 'UNKNOWN'

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (
                str(invoice_data.get('bookingNumber', '')),
                invoice_data.get('invoiceAmount'),
                status,
                invoice_id
            ))
            conn.commit()
            return True
    except Exception as e:
        logging.error(f"Erro ao atualizar invoice: {e}")
        return False


def agrupar_disputas_por_invoice(disputas: List[dict]) -> Dict[str, List[dict]]:
    """
    Agrupa disputas pelo número da invoice.
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
    Normaliza campos da disputa para o formato do banco.
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


def sincronizar_disputas_e_invoices():
    """
    FLUXO OTIMIZADO E CORRETO:
    1. Busca todas as disputas (1 chamada API)
    2. Para cada invoice com disputa:
       - Verifica se existe no banco
       - Se NÃO existe: busca da API de invoices e cria
       - Se existe E passou >2h: atualiza dados
       - Se existe E <2h: pula (não precisa atualizar)
    3. Salva as disputas

    RESULTADO: Sincroniza apenas 8-11 invoices ao invés de 604
    """

    logging.info("=" * 60)
    logging.info("SINCRONIZAÇÃO INTELIGENTE DE DISPUTAS E INVOICES")
    logging.info("=" * 60)

    # 1. Busca TODAS as disputas
    todas_disputas = buscar_todas_disputas_api()

    if not todas_disputas:
        logging.error("Não foi possível buscar disputas da API")
        return

    # 2. Agrupa por invoice
    logging.info("Agrupando disputas por invoice...")
    disputas_por_invoice = agrupar_disputas_por_invoice(todas_disputas)

    logging.info(f"Total de {len(disputas_por_invoice)} invoices têm disputas")
    logging.info("")

    # 3. Carrega invoices do banco para verificar quais existem
    logging.info("Carregando invoices do banco...")
    todas_invoices_banco = list_invoices(limit=None)
    invoice_map = {inv.numero_invoice: inv.id for inv in todas_invoices_banco}

    # 4. Processa cada invoice com disputa
    invoices_processadas = 0
    invoices_criadas = 0
    invoices_atualizadas = 0
    invoices_puladas = 0
    disputas_salvas = 0
    erros = 0

    duas_horas_atras = datetime.now() - timedelta(hours=2)

    for invoice_number, disputas in disputas_por_invoice.items():
        invoices_processadas += 1
        logging.info(
            f"[{invoices_processadas}/{len(disputas_por_invoice)}] "
            f"Invoice {invoice_number}: {len(disputas)} disputa(s)"
        )

        # Verifica se invoice existe no banco
        invoice_id = invoice_map.get(invoice_number)

        if not invoice_id:
            # Invoice NÃO existe - buscar da API e criar
            logging.info(f"  Invoice {invoice_number} não existe no banco, buscando da API...")

            invoice_data = buscar_invoice_da_api(invoice_number)

            if invoice_data:
                invoice_id = inserir_invoice_no_banco(invoice_data)
                if invoice_id:
                    invoices_criadas += 1
                    invoice_map[invoice_number] = invoice_id
                    logging.info(f"  Invoice {invoice_number} criada no banco (id={invoice_id})")
                else:
                    logging.error(f"  Erro ao criar invoice {invoice_number}")
                    erros += 1
                    continue
            else:
                logging.error(f"  Invoice {invoice_number} não encontrada na API")
                erros += 1
                continue
        else:
            # Invoice JÁ existe - verificar se precisa atualizar (>2h)
            sql_check = "SELECT updated_at FROM invoice WHERE id = %s"
            try:
                with get_conn() as conn, conn.cursor(dictionary=True) as cur:
                    cur.execute(sql_check, (invoice_id,))
                    row = cur.fetchone()

                    if row and row['updated_at']:
                        ultima_atualizacao = row['updated_at']

                        # Se foi atualizada há menos de 2 horas, PULA
                        if ultima_atualizacao >= duas_horas_atras:
                            invoices_puladas += 1
                            logging.info(
                                f"  Invoice {invoice_number} atualizada recentemente "
                                f"({ultima_atualizacao}), pulando"
                            )
                        else:
                            # Precisa atualizar (>2h)
                            invoice_data = buscar_invoice_da_api(invoice_number)
                            if invoice_data:
                                if atualizar_invoice_no_banco(invoice_id, invoice_data):
                                    invoices_atualizadas += 1
                                    logging.info(f"  Invoice {invoice_number} atualizada (id={invoice_id})")
                    else:
                        # Sem updated_at, atualiza por segurança
                        invoice_data = buscar_invoice_da_api(invoice_number)
                        if invoice_data:
                            if atualizar_invoice_no_banco(invoice_id, invoice_data):
                                invoices_atualizadas += 1
                                logging.info(f"  Invoice {invoice_number} atualizada (id={invoice_id})")
            except Exception as e:
                logging.error(f"  Erro ao verificar updated_at: {e}")
                invoices_puladas += 1

        # Salva as disputas da invoice
        for disputa in disputas:
            dispute_no = disputa.get('disputeNumber')
            status = disputa.get('status')

            if not status:
                logging.warning(f"  Disputa {dispute_no} sem status, ignorando")
                continue

            try:
                disputa_normalizada = normalizar_disputa(disputa)

                saved_id = upsert_disputa(
                    invoice_id=invoice_id,
                    dispute_number=dispute_no,
                    data=disputa_normalizada
                )

                disputas_salvas += 1
                logging.info(f"    Disputa {dispute_no} sincronizada (status={status}, id={saved_id})")

            except Exception as e:
                logging.error(f"    Erro ao salvar disputa {dispute_no}: {e}")
                erros += 1

    # Resumo
    logging.info("")
    logging.info("=" * 60)
    logging.info("Sincronização concluída:")
    logging.info(f"  - {len(todas_disputas)} disputas na API")
    logging.info(f"  - {len(disputas_por_invoice)} invoices com disputas")
    logging.info(f"  - {invoices_criadas} invoices criadas no banco")
    logging.info(f"  - {invoices_atualizadas} invoices atualizadas")
    logging.info(f"  - {invoices_puladas} invoices puladas (atualizadas recentemente)")
    logging.info(f"  - {disputas_salvas} disputas sincronizadas")
    if erros > 0:
        logging.info(f"  - {erros} erros")
    logging.info("=" * 60)


def atualizar_disputas_antigas(max_workers: int = 5):
    """
    Atualiza apenas disputas que precisam de refresh COM PARALELIZAÇÃO.
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
        from api_hapag.services.dispute_service import atualizar_status_disputa

        logging.info(
            f"[{idx}/{total}] Atualizando disputa {disp.dispute_number} "
            f"(id={disp.id}, status atual={disp.status})"
        )
        return atualizar_status_disputa(disp.id, disp.dispute_number)

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

    logging.info("")
    logging.info("=" * 60)
    logging.info("Atualização concluída:")
    logging.info(f"  - {total} disputas processadas")
    logging.info(f"  - {atualizadas} atualizadas com sucesso")
    if erros > 0:
        logging.info(f"  - {erros} erros")
    logging.info("=" * 60)