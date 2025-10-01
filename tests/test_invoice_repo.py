from api_hapag.repos.invoice_repo import list_invoices

if __name__ == "__main__":
    invoices = list_invoices(limit=5)
    for inv in invoices:
        print(f"{inv.id}\t{inv.numero_invoice}")
