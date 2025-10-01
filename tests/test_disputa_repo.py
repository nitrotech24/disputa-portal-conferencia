from api_hapag.repos.disputa_repo import insert_disputa, get_disputa_by_invoice

if __name__ == "__main__":
    # salva disputa fake para a invoice com id=1
    new_id = insert_disputa(invoice_id=1, status="ABERTA")
    print("Nova disputa salva com id:", new_id)

    # busca disputa da invoice 1
    disputa = get_disputa_by_invoice(1)
    print("Consulta disputa:", disputa)
