"""
main.py
Executa o fluxo completo de sincronizacao de disputas
"""

import sys
from pathlib import Path

# Adiciona o diretorio pai ao path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from api_hapag.utils.logger import setup_logger
from api_hapag.services.token_service import get_valid_token
from api_hapag.services.sync_service import sincronizar_disputas

logger = setup_logger()


def main():
    """
    Fluxo principal:
    1. Valida/renova token
    2. Sincroniza todas as disputas
    """
    logger.info("=" * 60)
    logger.info("INICIANDO SINCRONIZACAO DE DISPUTAS - HAPAG-LLOYD")
    logger.info("=" * 60)

    try:
        # Etapa 1: Garantir token valido
        logger.info("Etapa 1: Validando token...")
        token = get_valid_token()

        if not token:
            logger.error("Falha ao obter token valido. Abortando.")
            sys.exit(1)

        logger.info("Token validado com sucesso")

        # Etapa 2: Sincronizar todas as disputas
        logger.info("Etapa 2: Sincronizando todas as disputas...")
        sincronizar_disputas(limit=None)

        logger.info("=" * 60)
        logger.info("SINCRONIZACAO CONCLUIDA COM SUCESSO")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Erro na execucao: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()