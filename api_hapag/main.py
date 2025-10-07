"""
main.py
Executa o fluxo completo de sincronização de disputas
"""

import sys
from pathlib import Path

# Adiciona o diretório pai ao path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from api_hapag.utils.logger import setup_logger
from api_hapag.services.token_service import get_valid_token
from api_hapag.services.sync_service import (
    sincronizar_disputas,
    atualizar_disputas_antigas
)

# Importa função de sincronização de invoices
import logging
import requests
from api_hapag.config.db import get_conn


def sincronizar_invoices():
    """Sincroniza invoices da API com o banco"""
    from api_hapag.services.token_service import get_valid_token

    logger.info("=" * 60)
    logger.info("SINCRONIZAÇÃO DE INVOICES - HAPAG-LLOYD")
    logger.info("=" * 60)

    token = get_valid_token()
    if not token:
        logger.error("Não foi possível obter token válido")
        return

    url = "https://invoice-overview.api.hlag.cloud/api/invoices"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-token": token,
        "Accept": "application/json"
    }

    try:
        logger.info("Consultando API de invoices...")
        r = requests.get(url, headers=headers, timeout=30)

        if r.status_code != 200:
            logger.error(f"Erro {r.status_code}: {r.text}")
            return

        data = r.json()
        invoices = data.get('invoiceList', [])
        logger.info(f"✅ {len(invoices)} invoices retornadas da API")

        inseridas = 0
        atualizadas = 0
        erros = 0

        for idx, inv in enumerate(invoices, 1):
            if idx % 100 == 0:
                logger.info(f"Progresso: {idx}/{len(invoices)}...")

            invoice_num = str(inv.get('invoiceNumber'))
            statuses = inv.get('invoiceStatuses', [])
            status = statuses[0] if statuses else 'UNKNOWN'

            # Verifica se existe
            sql_check = "SELECT id FROM invoice WHERE numero_invoice = %s AND armador = 'HAPAG'"
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute(sql_check, (invoice_num,))
                exists = cur.fetchone()

            if exists:
                # Atualiza
                sql_update = """
                    UPDATE invoice SET numero_bl = %s, valor = %s, status = %s, 
                    updated_at = CURRENT_TIMESTAMP(3)
                    WHERE numero_invoice = %s AND armador = 'HAPAG'
                """
                with get_conn() as conn, conn.cursor() as cur:
                    cur.execute(sql_update, (
                        str(inv.get('bookingNumber')),
                        inv.get('invoiceAmount'),
                        status,
                        invoice_num
                    ))
                    conn.commit()
                atualizadas += 1
            else:
                # Insere
                sql_insert = """
                    INSERT INTO invoice (numero_invoice, armador, numero_bl, valor, status, updated_at)
                    VALUES (%s, 'HAPAG', %s, %s, %s, CURRENT_TIMESTAMP(3))
                """
                try:
                    with get_conn() as conn, conn.cursor() as cur:
                        cur.execute(sql_insert, (
                            invoice_num,
                            str(inv.get('bookingNumber')),
                            inv.get('invoiceAmount'),
                            status
                        ))
                        conn.commit()
                    inseridas += 1
                    if inseridas <= 10:
                        logger.info(f"  ✅ Nova: {invoice_num}")
                except Exception as e:
                    logger.error(f"Erro ao inserir {invoice_num}: {e}")
                    erros += 1

        logger.info("")
        logger.info("=" * 60)
        logger.info(f"✅ Invoices: {inseridas} novas, {atualizadas} atualizadas, {erros} erros")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Erro: {e}")
        import traceback
        traceback.print_exc()


logger = setup_logger()


def main():
    """
    Fluxo principal com 4 etapas:
    1. Valida/renova token
    2. Sincroniza invoices da API
    3. Sincroniza disputas das invoices
    4. Atualiza disputas antigas (>2h e não finalizadas)
    """
    logger.info("=" * 60)
    logger.info("SINCRONIZAÇÃO COMPLETA HAPAG-LLOYD")
    logger.info("=" * 60)

    try:
        # Etapa 1: Garantir token válido
        logger.info("Etapa 1: Validando token...")
        token = get_valid_token()

        if not token:
            logger.error("❌ Falha ao obter token válido. Abortando.")
            sys.exit(1)

        logger.info("✅ Token validado com sucesso")
        logger.info("")

        # Etapa 2: Sincronizar invoices
        logger.info("Etapa 2: Sincronizando invoices da API...")
        sincronizar_invoices()
        logger.info("")

        # Etapa 3: Sincronizar disputas
        logger.info("Etapa 3: Sincronizando disputas das invoices...")
        sincronizar_disputas(limit=None, max_workers=10)
        logger.info("")

        # Etapa 4: Atualizar disputas antigas
        logger.info("Etapa 4: Atualizando disputas desatualizadas...")
        atualizar_disputas_antigas(max_workers=5)
        logger.info("")

        logger.info("=" * 60)
        logger.info("✅ SINCRONIZAÇÃO COMPLETA CONCLUÍDA")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Sincronização interrompida pelo usuário")
        sys.exit(130)
    except Exception as e:
        logger.error(f"❌ Erro na execução: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def main_quick():
    """
    Modo rápido: apenas atualiza disputas antigas
    Útil para execução frequente (ex: cron a cada hora)
    """
    logger.info("=" * 60)
    logger.info("ATUALIZAÇÃO RÁPIDA - APENAS DISPUTAS ANTIGAS")
    logger.info("=" * 60)

    try:
        # Valida token
        logger.info("Validando token...")
        token = get_valid_token()

        if not token:
            logger.error("❌ Falha ao obter token válido. Abortando.")
            sys.exit(1)

        logger.info("✅ Token validado")
        logger.info("")

        # Atualiza apenas disputas antigas
        atualizar_disputas_antigas()
        logger.info("")

        logger.info("=" * 60)
        logger.info("✅ ATUALIZAÇÃO RÁPIDA CONCLUÍDA")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Erro na execução: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Verifica argumento da linha de comando
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        main_quick()
    else:
        main()