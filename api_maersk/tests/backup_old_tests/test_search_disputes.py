import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.token_service import TokenService
from services.auth_service import AuthService
from services.dispute_service import DisputeService

token_service = TokenService()
auth_service = AuthService(token_service)
ds = DisputeService(token_service, auth_service)

invoice = "7536709258"
customer = "305S3073SPA"

print(f"\n=== Buscando disputas da invoice {invoice} (POST) ===\n")

disputes = ds.search_disputes_by_invoice(invoice, customer)

if disputes:
    print(f"✅ Encontradas {len(disputes)} disputa(s)!")
    for d in disputes:
        print(f"\nDisputa: {d}")
else:
    print("❌ Nenhuma disputa encontrada")