import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api_maersk.services.token_service import TokenService
from api_maersk.services.auth_service import AuthService
from api_maersk.services.dispute_service import DisputeService
from api_maersk.services.dispute_sync_service_parallel import DisputeSyncServiceParallel
from api_maersk.repos.invoice_repository import InvoiceRepository
from api_maersk.repos.disputa_repository import DisputaRepository
from api_maersk.config.settings import CUSTOMER_CODE_MAPPING
import time


def main():
    print("=" * 80)
    print("SINCRONIZAÇÃO PARALELA - TODOS OS CLIENTES")
    print("=" * 80)

    # Inicializar serviços
    token_service = TokenService()
    auth_service = AuthService(token_service)
    dispute_service = DisputeService(token_service, auth_service)
    invoice_repo = InvoiceRepository()
    disputa_repo = DisputaRepository()

    # Serviço paralelo
    sync_service = DisputeSyncServiceParallel(
        dispute_service,
        invoice_repo,
        disputa_repo,
        max_workers=10
    )

    # Estatísticas globais
    total_stats = {
        "total_invoices": 0,
        "com_disputa": 0,
        "sem_disputa": 0,
        "disputas_salvas": 0,
        "erros": 0
    }

    start_time = time.time()

    # Processar cada cliente
    clientes = list(CUSTOMER_CODE_MAPPING.keys())

    for idx, customer_code in enumerate(clientes, 1):
        print(f"\n{'=' * 80}")
        print(f"CLIENTE {idx}/{len(clientes)}: {customer_code}")
        print(f"{'=' * 80}")

        try:
            # Sincronizar disputas deste cliente
            stats = sync_service.sync_disputes_parallel(
                customer_code=customer_code,
                limit=1000  # Ajuste conforme necessário
            )

            # Acumular estatísticas
            if "erro" not in stats:
                total_stats["total_invoices"] += stats.get("total_invoices", 0)
                total_stats["com_disputa"] += stats.get("com_disputa", 0)
                total_stats["sem_disputa"] += stats.get("sem_disputa", 0)
                total_stats["disputas_salvas"] += stats.get("disputas_salvas", 0)
                total_stats["erros"] += stats.get("erros", 0)

        except Exception as e:
            print(f"ERRO ao processar cliente {customer_code}: {e}")
            continue

    elapsed = time.time() - start_time

    # Resumo final
    print("\n" + "=" * 80)
    print("RESUMO FINAL - TODOS OS CLIENTES")
    print("=" * 80)
    print(f"Total de invoices processadas: {total_stats['total_invoices']}")
    print(f"Com disputa: {total_stats['com_disputa']}")
    print(f"Sem disputa: {total_stats['sem_disputa']}")
    print(f"Disputas salvas: {total_stats['disputas_salvas']}")
    print(f"Erros: {total_stats['erros']}")
    print(f"\nTempo total: {elapsed:.2f} segundos")

    if total_stats['total_invoices'] > 0:
        print(f"Velocidade: {total_stats['total_invoices'] / elapsed:.2f} invoices/segundo")

    print("=" * 80)


if __name__ == "__main__":
    main()