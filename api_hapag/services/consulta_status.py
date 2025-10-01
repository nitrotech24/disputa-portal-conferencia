"""
consulta_status.py
Consulta status de uma disputa na API da Hapag e atualiza no DB.
"""

import logging
import requests
from api_hapag.token_utils import get_valid_token
from api_hapag.repos.disputa_repo import update_disputa_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def atualizar_status_disputa(disputa_id: int, dispute_number: int) -> bool:
    """
    Consulta a disputa na API e atualiza o status no banco.
    - disputa_id: id no banco local
    - dispute_number: número da disputa na Hapag
    Retorna True se atualizou, False se deu erro.
    """
    token = get_valid_token()
    if not token:
        logging.error("❌ Não foi possível obter token válido para consulta.")
        return False

    url = f"https://dispute-overview.api.hlag.cloud/api/disputes/{dispute_number}"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-token": token,
        "Accept": "application/json"
    }

    try:
        r = requests.get(url, headers=headers, timeout=20)
        if r.status_code == 200:
            data = r.json()
            logging.info(f"🔎 Payload da API: {data}")

            # tentar várias chaves possíveis
            status = (
                data.get("status")
                or data.get("disputeStatus")
                or data.get("currentStatus")
            )

            if status:
                update_disputa_status(disputa_id, status)
                logging.info(f"✅ Disputa {dispute_number} atualizada para status={status}")
                return True
            else:
                logging.warning("⚠️ Não encontrei campo de status no JSON.")
                return False
        else:
            logging.error(f"Erro {r.status_code} ao consultar disputa: {r.text}")
            return False

    except requests.RequestException as e:
        logging.error(f"Erro na requisição: {e}")
        return False
