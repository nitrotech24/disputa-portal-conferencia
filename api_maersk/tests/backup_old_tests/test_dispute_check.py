import sys
from pathlib import Path
import json
# garante que a pasta raiz do projeto esteja no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.token_service import TokenService
from services.auth_service import AuthService
from services.dispute_service import DisputeService

token_service = TokenService()
auth_service = AuthService(token_service)
ds = DisputeService(token_service, auth_service)

invoice = "7536709258"
customer = "305S3073SPA"

print("=== TESTANDO OPÇÃO 1: /dispute ===")
disputes = ds.get_disputes_by_invoice(invoice, customer)
print(f"Resultado: {disputes}")

print("\n=== TESTANDO OPÇÃO 2: /invoices ===")
invoice_data = ds.get_invoice_info(invoice, customer, invoice_type="OPEN")
print(f"Resultado: {invoice_data}")

print("\n=== TESTANDO OPÇÃO 2: /invoices ===")
invoice_data = ds.get_invoice_info(invoice, customer, invoice_type="OPEN")


print("\n📋 RESPOSTA COMPLETA DA API:")
print(json.dumps(invoice_data, indent=2, ensure_ascii=False))