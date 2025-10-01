"""
consulta.py
Consulta detalhes de uma disputa na API da Hapag-Lloyd.
"""

import logging
import requests
from api_hapag.token_utils import get_valid_token

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def consultar_disputa(dispute_id: int) -> dict | None:
    """
    Consulta a disputa pelo ID, garantindo que o token esteja válido.
    """
    token = get_valid_token()
    if not token:
        logging.error("Não foi possível obter token válido para consulta.")
        return None

    url = f"https://dispute-overview.api.hlag.cloud/api/disputes/{dispute_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-token": token,
        "Accept": "application/json"
    }

    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            logging.info("Consulta realizada com sucesso ✅")
            return r.json()
        else:
            logging.error(f"Erro {r.status_code} ao consultar disputa: {r.text}")
            return None
    except requests.RequestException as e:
        logging.error(f"Erro na requisição: {e}")
        return None
