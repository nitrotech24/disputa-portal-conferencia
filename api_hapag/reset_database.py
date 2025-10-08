"""
reset_database.py
Script para limpar dados HAPAG do banco e recomeçar do zero
"""

import sys
from pathlib import Path

# Adiciona o diretório pai ao path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from api_hapag.config.db import get_conn
from api_hapag.utils.logger import setup_logger

logger = setup_logger()


def contar_registros():
    """Retorna contagem de invoices e disputas HAPAG"""
    sql_invoices = "SELECT COUNT(*) as total FROM invoice WHERE armador = 'HAPAG'"
    sql_disputas = """
        SELECT COUNT(*) as total FROM disputa 
        WHERE invoice_id IN (SELECT id FROM invoice WHERE armador = 'HAPAG')
    """

    try:
        with get_conn() as conn, conn.cursor(dictionary=True) as cur:
            cur.execute(sql_invoices)
            invoices = cur.fetchone()['total']

            cur.execute(sql_disputas)
            disputas = cur.fetchone()['total']

            return invoices, disputas
    except Exception as e:
        logger.error(f"Erro ao contar registros: {e}")
        return 0, 0


def limpar_disputas_hapag():
    """Remove todas as disputas de invoices HAPAG"""
    sql = """
        DELETE FROM disputa 
        WHERE invoice_id IN (
            SELECT id FROM invoice WHERE armador = 'HAPAG'
        )
    """

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql)
            deleted = cur.rowcount
            conn.commit()
            logger.info(f"Disputas removidas: {deleted}")
            return deleted
    except Exception as e:
        logger.error(f"Erro ao remover disputas: {e}")
        return 0


def limpar_invoices_hapag():
    """Remove todas as invoices HAPAG"""
    sql = "DELETE FROM invoice WHERE armador = 'HAPAG'"

    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(sql)
            deleted = cur.rowcount
            conn.commit()
            logger.info(f"Invoices removidas: {deleted}")
            return deleted
    except Exception as e:
        logger.error(f"Erro ao remover invoices: {e}")
        return 0


def main():
    logger.info("=" * 60)
    logger.info("RESET DO BANCO DE DADOS - APENAS HAPAG")
    logger.info("=" * 60)

    # Mostra estado atual
    invoices_antes, disputas_antes = contar_registros()
    logger.info(f"Estado atual do banco:")
    logger.info(f"  - Invoices HAPAG: {invoices_antes}")
    logger.info(f"  - Disputas HAPAG: {disputas_antes}")
    logger.info("")

    # Confirma com usuário
    resposta = input("Tem certeza que deseja LIMPAR todos os dados HAPAG? (sim/não): ")

    if resposta.lower() not in ['sim', 's', 'yes', 'y']:
        logger.info("Operação cancelada pelo usuário")
        return

    logger.info("")
    logger.info("Iniciando limpeza...")
    logger.info("")

    # Limpa disputas primeiro (FK)
    logger.info("1. Removendo disputas...")
    disputas_removidas = limpar_disputas_hapag()

    # Limpa invoices
    logger.info("2. Removendo invoices...")
    invoices_removidas = limpar_invoices_hapag()

    # Verifica estado final
    logger.info("")
    invoices_depois, disputas_depois = contar_registros()
    logger.info(f"Estado após limpeza:")
    logger.info(f"  - Invoices HAPAG: {invoices_depois}")
    logger.info(f"  - Disputas HAPAG: {disputas_depois}")

    logger.info("")
    logger.info("=" * 60)
    logger.info("LIMPEZA CONCLUÍDA")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Para sincronizar novamente, execute:")
    logger.info("  python main.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("\nOperação cancelada pelo usuário")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Erro na execução: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)