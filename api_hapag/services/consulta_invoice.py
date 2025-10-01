"""
consulta_invoice.py
Consulta disputas relacionadas a uma invoice na API da Hapag-Lloyd.
"""

import logging
import requests
from api_hapag.token_utils import get_valid_token  # garante o token válido

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def consultar_invoice(invoice_number: str) -> dict | None:
    """
    Consulta a invoice pelo número, garantindo que o token esteja válido.
    Retorna os detalhes da disputa se encontrados.
    """
    token = get_valid_token()
    if not token:
        logging.error("❌ Não foi possível obter token válido para consulta.")
        return None

    # URL base da API
    url = "https://dispute-overview.api.hlag.cloud/api/disputes"

    headers = {
        "Authorization": f"Bearer {token}",
        "x-token": token,
        "Accept": "application/json"
    }

    # 👉 Primeira tentativa com GET
    try:
        r = requests.get(f"{url}?invoiceNumber={invoice_number}", headers=headers, timeout=20)
        if r.status_code == 200:
            logging.info("Consulta (GET) realizada com sucesso ✅")
            return r.json()
        elif r.status_code == 404:
            logging.warning(f"Invoice {invoice_number} não encontrada (404).")
            return None
        else:
            logging.warning(f"GET retornou {r.status_code}, tentando POST...")

            # 👉 fallback para POST (alguns endpoints usam POST para busca)
            payload = {"invoiceNumber": invoice_number}
            r = requests.post(url, headers=headers, json=payload, timeout=20)

            if r.status_code == 200:
                logging.info("Consulta (POST) realizada com sucesso ✅")
                return r.json()
            else:
                logging.error(f"Erro {r.status_code} ao consultar invoice: {r.text}")
                return None

    except requests.RequestException as e:
        logging.error(f"Erro na requisição: {e}")
        return None
