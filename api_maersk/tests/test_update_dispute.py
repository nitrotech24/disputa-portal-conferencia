import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.token_service import TokenService
from services.auth_service import AuthService
from services.dispute_service import DisputeService
from services.dispute_sync_service import DisputeSyncService
from repos.invoice_repository import InvoiceRepository
from repos.disputa_repository import DisputaRepository


def main():
    # Inicializar serviços
    token_service = TokenService()
    auth_service = AuthService(token_service)
    dispute_service = DisputeService(token_service, auth_service)

    invoice_repo = InvoiceRepository()
    disputa_repo = DisputaRepository()

    sync_service = DisputeSyncService(dispute_service, invoice_repo, disputa_repo)

    # Atualizar status de uma disputa específica
    dispute_id = "23724918"
    customer_code = "305S3073SPA"

    print(f"\n=== Atualizando disputa {dispute_id} ===\n")

    result = sync_service.update_dispute_status(dispute_id, customer_code)

    if result["success"]:
        print(f"✅ Sucesso!")
        print(f"Disputa: {result['dispute_id']}")
        print(f"Invoice: {result['invoice_number']}")
        print(f"Status: {result['status']}")
    else:
        print(f"❌ Erro: {result['error']}")


if __name__ == "__main__":
    main()