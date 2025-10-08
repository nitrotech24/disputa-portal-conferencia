"""
main.py
Executa o fluxo completo de sincronização de disputas
OTIMIZADO: Busca global de disputas + Processamento em lote
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
from api_hapag.services.sync_invoices import sincronizar_invoices

logger = setup_logger()


def main():
    """
    Fluxo principal OTIMIZADO:
    1. Valida/renova token
    2. Sincroniza invoices da API (processamento em lote)
    3. Sincroniza disputas (busca global, 1 chamada à API)
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
            logger.error("Falha ao obter token válido. Abortando.")
            sys.exit(1)

        logger.info("Token validado com sucesso")
        logger.info("")

        # Etapa 2: Sincronizar invoices (OTIMIZADO: batch operations)
        logger.info("Etapa 2: Sincronizando invoices da API...")
        sincronizar_invoices()
        logger.info("")

        # Etapa 3: Sincronizar disputas (OTIMIZADO: 1 chamada global)
        logger.info("Etapa 3: Sincronizando disputas...")
        sincronizar_disputas()
        logger.info("")

        # Etapa 4: Atualizar disputas antigas
        logger.info("Etapa 4: Atualizando disputas desatualizadas...")
        atualizar_disputas_antigas(max_workers=5)
        logger.info("")

        logger.info("=" * 60)
        logger.info("SINCRONIZAÇÃO COMPLETA CONCLUÍDA")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.warning("\nSincronização interrompida pelo usuário")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Erro na execução: {e}")
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
            logger.error("Falha ao obter token válido. Abortando.")
            sys.exit(1)

        logger.info("Token validado")
        logger.info("")

        # Atualiza apenas disputas antigas
        atualizar_disputas_antigas(max_workers=5)
        logger.info("")

        logger.info("=" * 60)
        logger.info("ATUALIZAÇÃO RÁPIDA CONCLUÍDA")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.warning("\nAtualização interrompida pelo usuário")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Erro na execução: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Verifica argumento da linha de comando
    if len(sys.argv) > 1:
        if sys.argv[1] == "--quick":
            main_quick()
        else:
            print("Uso: python main.py [--quick]")
            print("  (sem argumentos): sincronização completa")
            print("  --quick: apenas atualiza disputas antigas")
            sys.exit(1)
    else:
        main()