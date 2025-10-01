"""
sync_disputes.py
Script principal - Sincroniza disputas da API Hapag com o banco
"""

import sys
sys.path.insert(0, '..')

from api_hapag.services.sync_service import sincronizar_disputas
from api_hapag.utils.logger import setup_logger

logger = setup_logger()

def main():
    logger.info("=" * 60)
    logger.info("SINCRONIZAÇÃO DE DISPUTAS - HAPAG-LLOYD")
    logger.info("=" * 60)

    limit = 10  # Alterar conforme necessário

    try:
        sincronizar_disputas(limit=limit)
        logger.info("")
        logger.info("=" * 60)
        logger.info("SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"Erro na sincronização: {e}")
        raise

if __name__ == "__main__":
    main()
