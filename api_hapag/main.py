"""
main.py
Ponto de entrada principal da API Hapag
"""

import sys
import logging
from pathlib import Path

# Adiciona o diretorio raiz ao path
sys.path.insert(0, str(Path(__file__).parent))

from api_hapag.utils.logger import setup_logger
from api_hapag.services.sync_service import sincronizar_disputas
from api_hapag.services.token_service import get_valid_token

logger = setup_logger()


def exibir_menu():
    """Exibe menu de opcoes"""
    print("\n" + "=" * 60)
    print("API HAPAG-LLOYD - GESTAO DE DISPUTAS")
    print("=" * 60)
    print("\n1. Sincronizar disputas")
    print("2. Renovar token manualmente")
    print("3. Testar token atual")
    print("0. Sair")
    print("\n" + "=" * 60)


def sincronizar():
    """Executa sincronizacao de disputas"""
    try:
        limit = input("\nQuantas invoices deseja sincronizar? (padrao: 10): ").strip()
        limit = int(limit) if limit else 10
        
        logger.info("Iniciando sincronizacao...")
        sincronizar_disputas(limit=limit)
        logger.info("Sincronizacao concluida com sucesso")
        
    except ValueError:
        logger.error("Valor invalido. Use apenas numeros.")
    except Exception as e:
        logger.error(f"Erro na sincronizacao: {e}")


def renovar_token():
    """Renova token via login Selenium"""
    from api_hapag.services.auth_service import login_and_get_token
    
    logger.info("Renovando token via Selenium...")
    token = login_and_get_token()
    
    if token:
        logger.info("Token renovado com sucesso")
    else:
        logger.error("Falha ao renovar token")


def testar_token():
    """Testa se