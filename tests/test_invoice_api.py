from api_hapag.services.consulta_invoice import consultar_invoice

if __name__ == "__main__":
    invoice_no = "2014860578"  # troca por uma invoice real sua
    result = consultar_invoice(invoice_no)
    print("Resultado consulta invoice:", result)
