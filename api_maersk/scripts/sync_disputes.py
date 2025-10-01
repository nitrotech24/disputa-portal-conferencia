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

    # roda sync para até 5 invoices MAERSK
    sync_service.sync_disputes(customer_code="305S3073SPA", limit=100)

if __name__ == "__main__":
    main()
