"""
sync_invoices.py
Sincroniza invoices da API Hapag com o banco de dados
"""

import sys

sys.path.insert(0, '..')

import logging
import requests
from typing import Optional
from api_hapag.services.token_service import get_valid_token
from api_hapag.config.db import get_conn
from api_hapag.utils.logger import setup_logger

logger = setup_logger()


def buscar_invoices_api() -> list | None:
    """
    Busca todas as invoices da API Hapag

    Returns:
        Lista de invoices ou None se erro
    """
    token = get_valid_token()
    if not token:
        logger.error("Não foi possível obter token válido")
        return None

    url = "https://invoice-overview.api.hlag.cloud/api/invoices"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-token": token,
        "Accept": "application/json"
    }

    try:
        logger.info("Consultando API de invoices...")
        r = requests.get(url, headers=headers, timeout=30)

        if r.status_code == 200:
            data = r.json()
            invoices = data.get('invoiceList', [])
            logger.info(f"✅ {len(invoices)} invoices retornadas da API")
            return invoices
        else:
            logger.error(f"Erro {r.status_code}: {r.text}")
            return None

    except requests.RequestException as e:
        logger.error(f"Erro na requisição: {e}")
        return None


def invoice_existe_no_bd(invoice_number: str) -> bool:
    """Verifica se invoice já existe no banco"""
    sql = "SELECT id FROM invoice WHERE numero_invoice = %s AND armador = 'HAPAG' LIMIT 1"

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (invoice_number,))
        return cur.fetchone() is not None


def inserir_invoice(invoice_data: dict) -> int | None:
    """
    Insere nova invoice no banco

    Args:
        invoice_data: Dicionário com dados da API

    Returns:
        ID da invoice inserida ou None se erro
    """
    sql = """
        INSERT INTO invoice (
            numero_invoice, 
            armador,
            numero_bl,
            valor,
            status,
            created_at
        ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP(3))
    """

    # Pega primeiro status da lista
    statuses = invoice_data.get('invoiceStatuses', [])
    status = statuses[0] if statuses else 'UNKNOWN'

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (
                str(invoice_data.get('invoiceNumber')),
                'HAPAG',
                str(invoice_data.get('bookingNumber')),
                invoice_data.get('invoiceAmount'),
                status
            ))
            conn.commit()
            return cur.lastrowid
    except Exception as e:
        logger.error(f"Erro ao inserir invoice {invoice_data.get('invoiceNumber')}: {e}")
        return None


def atualizar_invoice(invoice_data: dict) -> bool:
    """
    Atualiza invoice existente no banco

    Args:
        invoice_data: Dicionário com dados da API

    Returns:
        True se atualizou, False se erro
    """
    sql = """
        UPDATE invoice
        SET booking_number = %s,
            invoice_amount = %s,
            invoice_status = %s,
            updated_at = NOW()
        WHERE numero_invoice = %s
          AND armador = 'HAPAG'
    """

    # Pega primeiro status da lista
    statuses = invoice_data.get('invoiceStatuses', [])
    status = statuses[0] if statuses else 'UNKNOWN'

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (
                invoice_data.get('bookingNumber'),
                invoice_data.get('invoiceAmount'),
                status,
                str(invoice_data.get('invoiceNumber'))
            ))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Erro ao atualizar invoice {invoice_data.get('invoiceNumber')}: {e}")
        return False


def sincronizar_invoices():
    """
    Sincroniza invoices da API com o banco de dados
    """
    logger.info("=" * 60)
    logger.info("SINCRONIZAÇÃO DE INVOICES - HAPAG-LLOYD")
    logger.info("=" * 60)

    # Busca invoices da API
    invoices_api = buscar_invoices_api()

    if not invoices_api:
        logger.error("❌ Não foi possível buscar invoices da API")
        return

    total = len(invoices_api)
    inseridas = 0
    atualizadas = 0
    erros = 0

    logger.info(f"Processando {total} invoices...")
    logger.info("")

    for idx, inv_data in enumerate(invoices_api, 1):
        invoice_number = str(inv_data.get('invoiceNumber'))

        # Progress log a cada 50 invoices
        if idx % 50 == 0:
            logger.info(f"Progresso: {idx}/{total} invoices processadas...")

        # Verifica se já existe
        if invoice_existe_no_bd(invoice_number):
            # Atualiza
            if atualizar_invoice(inv_data):
                atualizadas += 1
            else:
                erros += 1
        else:
            # Insere nova
            if inserir_invoice(inv_data):
                inseridas += 1
                logger.info(f"  ✅ Nova invoice inserida: {invoice_number}")
            else:
                erros += 1

    # Resumo
    logger.info("")
    logger.info("=" * 60)
    logger.info("✅ Sincronização de invoices concluída:")
    logger.info(f"   - {total} invoices processadas")
    logger.info(f"   - {inseridas} novas inseridas")
    logger.info(f"   - {atualizadas} atualizadas")
    if erros > 0:
        logger.info(f"   - ⚠️  {erros} erros")
    logger.info("=" * 60)


def main():
    try:
        sincronizar_invoices()
    except Exception as e:
        logger.error(f"Erro na execução: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()