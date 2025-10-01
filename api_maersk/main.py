"""
API Maersk - Sistema de Gestão de Disputas
Ponto de entrada principal da aplicação
"""
import sys
from services.token_service import TokenService
from services.auth_service import AuthService
from services.dispute_service import DisputeService
from services.dispute_sync_service_parallel import DisputeSyncServiceParallel
from repos.invoice_repository import InvoiceRepository
from repos.disputa_repository import DisputaRepository
from config.settings import CUSTOMER_CODE_MAPPING
from utils.logger import setup_logger
import time

logger = setup_logger(__name__)


def importar_invoices_faltantes(customer_code: str, dispute_service: DisputeService, invoice_repo: InvoiceRepository):
    """
    Identifica e importa invoices que têm disputa mas não estão no banco.
    """
    from scripts.import_missing_invoices import get_missing_invoices_from_disputes, fetch_and_insert_missing_invoices

    logger.info(f"[1/2] Verificando invoices faltantes para {customer_code}...")
    missing_invoices = get_missing_invoices_from_disputes(customer_code)

    if missing_invoices:
        logger.info(f"Encontradas {len(missing_invoices)} invoices faltantes")
        stats = fetch_and_insert_missing_invoices(customer_code, missing_invoices)
        return stats.get('inseridas_banco', 0)
    else:
        logger.info("Nenhuma invoice faltante")
        return 0


def main():
    print("=" * 80)
    print("EXECUÇÃO AUTOMÁTICA COMPLETA - API MAERSK")
    print("=" * 80)
    print("\nEste processo irá:")
    print("1. Importar invoices com disputa que não estão no banco")
    print("2. Sincronizar todas as disputas")
    print("=" * 80)

    # Inicializar serviços
    logger.info("Inicializando serviços...")
    token_service = TokenService()
    auth_service = AuthService(token_service)
    dispute_service = DisputeService(token_service, auth_service)
    invoice_repo = InvoiceRepository()
    disputa_repo = DisputaRepository()
    sync_service = DisputeSyncServiceParallel(
        dispute_service,
        invoice_repo,
        disputa_repo,
        max_workers=3
    )

    # Processar todos os clientes
    clientes = list(CUSTOMER_CODE_MAPPING.keys())
    total_disputas = 0
    total_invoices_importadas = 0

    start_time = time.time()

    for idx, customer_code in enumerate(clientes, 1):
        print(f"\n{'=' * 80}")
        print(f"CLIENTE {idx}/{len(clientes)}: {customer_code}")
        print(f"{'=' * 80}")

        try:
            # Passo 1: Importar invoices faltantes
            invoices_importadas = importar_invoices_faltantes(customer_code, dispute_service, invoice_repo)
            total_invoices_importadas += invoices_importadas

            if invoices_importadas > 0:
                logger.info(f"✅ {invoices_importadas} invoices importadas")

            # Passo 2: Sincronizar disputas
            logger.info(f"[2/2] Sincronizando disputas...")
            stats = sync_service.sync_disputes_parallel(customer_code, limit=10000)

            if "erro" not in stats:
                total_disputas += stats.get("disputas_salvas", 0)

                print(f"\nResultado:")
                print(f"  Invoices importadas: {invoices_importadas}")
                print(f"  Total invoices: {stats.get('total_invoices', 0)}")
                print(f"  Com disputa: {stats.get('com_disputa', 0)}")
                print(f"  Disputas salvas: {stats.get('disputas_salvas', 0)}")

        except Exception as e:
            logger.error(f"Erro ao processar {customer_code}: {e}")
            continue

    elapsed = time.time() - start_time

    # Resumo final
    print(f"\n{'=' * 80}")
    print("EXECUÇÃO CONCLUÍDA")
    print(f"{'=' * 80}")
    print(f"Total de clientes processados: {len(clientes)}")
    print(f"Total de invoices importadas: {total_invoices_importadas}")
    print(f"Total de disputas sincronizadas: {total_disputas}")
    print(f"Tempo total: {elapsed:.1f} segundos")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nPrograma interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        sys.exit(1)