import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from repos.invoice_repository import InvoiceRepository


def main():
    repo = InvoiceRepository()
    invoices = repo.fetch_invoices_maersk(limit=5)
    print(f"✅ Encontradas {len(invoices)} invoices MAERSK")
    for inv in invoices:
        print(f" - id={inv['id']}, numero_invoice={inv['numero_invoice']}")

if __name__ == "__main__":
    main()
