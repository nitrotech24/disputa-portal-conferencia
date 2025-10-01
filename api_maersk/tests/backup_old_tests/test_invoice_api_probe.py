import sys
import json
from pathlib import Path

# garante que a pasta raiz do projeto esteja no sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.token_service import TokenService
from services.auth_service import AuthService
from services.dispute_service import DisputeService


def probe_invoice(invoice_number: str, customer_code: str, invoice_type: str = "OPEN"):
    """Executa chamada ao /invoices e imprime resumo para debug."""
    token_service = TokenService()
    auth_service = AuthService(token_service)
    ds = DisputeService(token_service, auth_service)

    print(f"\n=== Testando /invoices ===")
    print(f"invoice_number={invoice_number}, customer_code={customer_code}, invoice_type={invoice_type}")

    payload = ds.get_invoice_info(invoice_number, customer_code, invoice_type=invoice_type)

    if not payload:
        print("❌ Nenhum payload retornado (erro 500 ou token inválido).")
        return

    if isinstance(payload, dict) and "invoices" in payload and isinstance(payload["invoices"], list):
        invoices = payload["invoices"]
        print(f"✅ API retornou {len(invoices)} invoice(s)")

        if invoices:
            inv0 = invoices[0]
            # imprime campos relevantes se existirem
            for k in ["invoiceNumber", "status", "hasDispute", "disputeId", "disputeNumber", "disputeStatus"]:
                if k in inv0:
                    print(f" - {k}: {inv0[k]}")

            # imprime primeiras chaves para análise
            print("Chaves da primeira invoice:", list(inv0.keys())[:30])

            # opcional: imprimir parte do JSON completo
            print("\nPreview JSON:")
            print(json.dumps(inv0, indent=2)[:1000], "...")
    else:
        print("ℹ️ Payload não contém 'invoices' como lista.")
        if isinstance(payload, dict):
            print("Chaves top-level:", list(payload.keys()))
        else:
            print("Tipo inesperado:", type(payload))


def main():
    # ⚠️ ajuste aqui para os mesmos valores do DevTools
    customer_code = "305S3073SPA"   # exatamente como aparece no DevTools
    invoice_number = "7536709258"   # número de exemplo

    # testa tanto OPEN quanto PAID
    probe_invoice(invoice_number, customer_code, invoice_type="OPEN")
    probe_invoice(invoice_number, customer_code, invoice_type="PAID")


if __name__ == "__main__":
    main()
