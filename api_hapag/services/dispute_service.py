"""
dispute_service.py
Serviço para consultar disputas na API da Hapag-Lloyd.
Consolidação de consulta_disputa.py, consulta_invoice.py e consulta_status.py
"""

import logging
import requests
from api_hapag.services.token_service import get_valid_token
from api_hapag.repos.dispute_repository import update_disputa_status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def consultar_disputa(dispute_id):
    """Consulta detalhes de uma disputa específica"""
    token = get_valid_token()
    if not token:
        logging.error("Não foi possível obter token válido")
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
            logging.info("Consulta realizada com sucesso")
            return r.json()
        else:
            logging.error(f"Erro {r.status_code}: {r.text}")
            return None
    except requests.RequestException as e:
        logging.error(f"Erro na requisição: {e}")
        return None


def consultar_invoice(invoice_number):
    """Consulta disputas relacionadas a uma invoice"""
    token = get_valid_token()
    if not token:
        logging.error("Não foi possível obter token válido")
        return None

    url = "https://dispute-overview.api.hlag.cloud/api/disputes"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-token": token,
        "Accept": "application/json"
    }

    try:
        r = requests.get(f"{url}?invoiceNumber={invoice_number}", headers=headers, timeout=20)
        if r.status_code == 200:
            logging.info("Consulta GET realizada com sucesso")
            return r.json()
        elif r.status_code == 404:
            logging.warning(f"Invoice {invoice_number} não encontrada")
            return None
        else:
            payload = {"invoiceNumber": invoice_number}
            r = requests.post(url, headers=headers, json=payload, timeout=20)
            if r.status_code == 200:
                logging.info("Consulta POST realizada com sucesso")
                return r.json()
            else:
                logging.error(f"Erro {r.status_code}: {r.text}")
                return None
    except requests.RequestException as e:
        logging.error(f"Erro na requisição: {e}")
        return None


def atualizar_status_disputa(disputa_id, dispute_number):
    """Atualiza status de uma disputa consultando a API"""
    token = get_valid_token()
    if not token:
        logging.error("Não foi possível obter token válido")
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
            status = data.get("status") or data.get("disputeStatus") or data.get("currentStatus")
            if status:
                update_disputa_status(disputa_id, status)
                logging.info(f"Disputa {dispute_number} atualizada para status={status}")
                return True
            else:
                logging.warning("Campo de status não encontrado")
                return False
        else:
            logging.error(f"Erro {r.status_code}: {r.text}")
            return False
    except requests.RequestException as e:
        logging.error(f"Erro na requisição: {e}")
        return False
