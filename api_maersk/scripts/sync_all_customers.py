import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.token_service import TokenService
from services.auth_service import AuthService
from services.dispute_service import DisputeService
from services.dispute_sync_service import DisputeSyncService
from repos.invoice_repository import InvoiceRepository
from repos.disputa_repository import DisputaRepository
from utils.logger import setup_logger
import time

logger = setup_logger(__name__)


def sync_single_customer(customer_code: str, customer_name: str):
    """
    Sincroniza invoices e disputas de um único cliente.
    """
    logger.info("=" * 80)
    logger.info(f"PROCESSANDO CLIENTE: {customer_name} ({customer_code})")
    logger.info("=" * 80)

    # Inicializar serviços
    token_service = TokenService()
    auth_service = AuthService(token_service)
    dispute_service = DisputeService(token_service, auth_service)
    invoice_repo = InvoiceRepository()
    disputa_repo = DisputaRepository()
    sync_service = DisputeSyncService(dispute_service, invoice_repo, disputa_repo)

    # Importar invoices faltantes
    logger.info(f"\n[1] Importando invoices faltantes...")
    from tests.import_missing_invoices import get_missing_invoices_from_disputes, fetch_and_insert_missing_invoices

    missing_invoices = get_missing_invoices_from_disputes(customer_code)

    if missing_invoices:
        logger.info(f"Encontradas {len(missing_invoices)} invoices faltantes")
        stats_import = fetch_and_insert_missing_invoices(customer_code, missing_invoices)
        logger.info(f"✅ Importadas: {stats_import['inseridas_banco']} invoices")
    else:
        logger.info("✅ Nenhuma invoice faltante")

    # Sincronizar disputas
    logger.info(f"\n[2] Sincronizando disputas...")
    stats_sync = sync_service.sync_disputes(customer_code, limit=10000)

    logger.info("\n" + "=" * 80)
    logger.info(f"RESUMO - {customer_name}")
    logger.info("=" * 80)
    logger.info(f"Invoices importadas: {stats_import.get('inseridas_banco', 0) if missing_invoices else 0}")
    logger.info(f"Disputas sincronizadas: {stats_sync.get('disputas_salvas', 0)}")
    logger.info(f"Taxa de cobertura: {stats_sync.get('com_disputa', 0)}/{stats_sync.get('total_invoices', 0)}")
    logger.info("=" * 80)

    return stats_sync


def sync_all_customers():
    """
    Processa TODOS os 5 clientes automaticamente.
    """
    logger.info("\n" + "=" * 80)
    logger.info("SINCRONIZAÇÃO DE TODOS OS CLIENTES")
    logger.info("=" * 80)

    # Inicializar TokenService para pegar lista de clientes
    token_service = TokenService()
    all_customers = token_service.get_all_customers()

    if not all_customers:
        logger.error("Nenhum cliente encontrado no arquivo de tokens!")
        return

    logger.info(f"\n📋 Total de clientes: {len(all_customers)}")
    for code, data in all_customers.items():
        logger.info(f"  - {data.get('name', 'Unknown')[:50]} ({code})")

    logger.info("\n⏱️  Tempo estimado total: ~{} minutos".format(len(all_customers) * 5))
    logger.info("\nIniciando em 5 segundos... (Ctrl+C para cancelar)\n")
    time.sleep(5)

    # Estatísticas globais
    global_stats = {
        "total_clientes": len(all_customers),
        "clientes_processados": 0,
        "total_invoices": 0,
        "total_disputas": 0,
        "clientes_com_erro": []
    }

    # Processar cada cliente
    for idx, (customer_code, customer_data) in enumerate(all_customers.items(), 1):
        customer_name = customer_data.get('name', 'Unknown')

        try:
            logger.info(f"\n{'#' * 80}")
            logger.info(f"CLIENTE {idx}/{len(all_customers)}")
            logger.info(f"{'#' * 80}\n")

            stats = sync_single_customer(customer_code, customer_name)

            global_stats["clientes_processados"] += 1
            global_stats["total_disputas"] += stats.get("disputas_salvas", 0)

            # Pausa entre clientes para não sobrecarregar API
            if idx < len(all_customers):
                logger.info(f"\n⏸️  Pausa de 10s antes do próximo cliente...\n")
                time.sleep(10)

        except Exception as e:
            logger.error(f"❌ Erro ao processar {customer_name}: {e}")
            global_stats["clientes_com_erro"].append(customer_name)
            continue

    # Relatório final global
    logger.info("\n" + "=" * 80)
    logger.info("RELATÓRIO FINAL GLOBAL")
    logger.info("=" * 80)
    logger.info(f"📊 Total de clientes: {global_stats['total_clientes']}")
    logger.info(f"✅ Clientes processados: {global_stats['clientes_processados']}")
    logger.info(f"💾 Total de disputas sincronizadas: {global_stats['total_disputas']}")

    if global_stats["clientes_com_erro"]:
        logger.warning(f"\n⚠️  Clientes com erro ({len(global_stats['clientes_com_erro'])}):")
        for cliente in global_stats["clientes_com_erro"]:
            logger.warning(f"  - {cliente}")

    logger.info("\n" + "=" * 80)
    logger.info("✅ SINCRONIZAÇÃO COMPLETA!")
    logger.info("=" * 80)


def main():
    """
    Processa TODOS os clientes automaticamente sem perguntar.
    """
    sync_all_customers()


if __name__ == "__main__":
    main()