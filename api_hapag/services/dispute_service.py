"""
dispute_service.py
Serviço para consultar disputas na API da Hapag-Lloyd.
"""

import logging
import requests
from api_hapag.services.token_service import get_valid_token
from api_hapag.repos.dispute_repository import update_disputa_completa

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def consultar_disputa(dispute_number: int) -> dict | None:
    """
    Consulta detalhes completos de uma disputa específica na API.

    Args:
        dispute_number: Número da disputa na Hapag

    Returns:
        Dicionário com dados normalizados da disputa ou None se erro
    """
    from api_hapag.utils.storage import load_token
    token = load_token()

    if not token:
        logging.error("Token não encontrado")
        return None

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
            logging.info(f"Disputa {dispute_number} consultada com sucesso")

            # Valida se tem status (campo obrigatório)
            status = data.get('status') or data.get('disputeStatus') or data.get('currentStatus')
            if not status:
                logging.warning(f"Disputa {dispute_number}: status não encontrado na API")
                return None

            # Normaliza campos da API para o formato do banco
            return {
                'status': status,
                'dispute_reason': data.get('dispute_reason'),
                'amount': data.get('amount'),
                'currency': data.get('currency'),
                'ref': data.get('ref'),
                'allowSecondReview': data.get('allowSecondReview'),
                'disputeCreated': data.get('disputeCreated'),
                'invoiceNumber': data.get('invoiceNumber'),
                'disputeNumber': data.get('disputeNumber')
            }
        elif r.status_code == 404:
            logging.warning(f"Disputa {dispute_number} não encontrada")
            return None
        else:
            logging.error(f"Erro {r.status_code}: {r.text}")
            return None
    except requests.RequestException as e:
        logging.error(f"Erro na requisição: {e}")
        return None


def consultar_invoice(invoice_number: str) -> list | None:
    """
    Consulta disputas relacionadas a uma invoice.
    Retorna lista de disputas com todos os campos normalizados.

    Args:
        invoice_number: Número da invoice

    Returns:
        Lista de dicionários com dados das disputas
    """
    from api_hapag.utils.storage import load_token
    token = load_token()

    if not token:
        logging.error("Token não encontrado")
        return None

    url = "https://dispute-overview.api.hlag.cloud/api/disputes"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-token": token,
        "Accept": "application/json"
    }

    try:
        # Tenta GET primeiro
        r = requests.get(f"{url}?invoiceNumber={invoice_number}", headers=headers, timeout=20)

        if r.status_code == 200:
            logging.info(f"Invoice {invoice_number}: disputas encontradas via GET")
            return _normalizar_disputas(r.json())

        elif r.status_code == 404:
            # Se não encontrou via GET, tenta POST
            logging.info(f"Invoice {invoice_number}: tentando POST...")
            payload = {"invoiceNumber": invoice_number}
            r = requests.post(url, headers=headers, json=payload, timeout=20)

            if r.status_code == 200:
                logging.info(f"Invoice {invoice_number}: disputas encontradas via POST")
                return _normalizar_disputas(r.json())
            else:
                logging.warning(f"Invoice {invoice_number}: não encontrada")
                return None
        else:
            logging.error(f"Erro {r.status_code}: {r.text}")
            return None

    except requests.RequestException as e:
        logging.error(f"Erro na requisição: {e}")
        return None


def _normalizar_disputas(data: list | dict) -> list:
    """
    Normaliza resposta da API para formato padronizado.
    A API pode retornar lista ou objeto único.
    """
    if not data:
        return []

    # Se for dicionário único, converte para lista
    if isinstance(data, dict):
        data = [data]

    disputas_normalizadas = []
    for d in data:
        # Valida se tem status (campo obrigatório)
        status = d.get('status') or d.get('disputeStatus') or d.get('currentStatus')
        if not status:
            logging.warning(f"Disputa {d.get('disputeNumber')}: status não encontrado, ignorando")
            continue

        disputas_normalizadas.append({
            'disputeNumber': d.get('disputeNumber'),
            'status': status,
            'dispute_reason': d.get('dispute_reason'),
            'amount': d.get('amount'),
            'currency': d.get('currency'),
            'ref': d.get('ref'),
            'allowSecondReview': d.get('allowSecondReview'),
            'disputeCreated': d.get('disputeCreated'),
            'invoiceNumber': d.get('invoiceNumber')
        })

    return disputas_normalizadas


def atualizar_status_disputa(disputa_id: int, dispute_number: int) -> bool:
    """
    Atualiza status e dados completos de uma disputa consultando a API.
    Usado para atualizar disputas antigas (>2h).

    Args:
        disputa_id: ID da disputa no banco
        dispute_number: Número da disputa na Hapag

    Returns:
        True se atualizou com sucesso, False caso contrário
    """
    data = consultar_disputa(dispute_number)

    if not data:
        logging.error(f"Não foi possível consultar disputa {dispute_number}")
        return False

    try:
        update_disputa_completa(disputa_id, data)
        logging.info(
            f"Disputa {dispute_number} (id={disputa_id}) atualizada: "
            f"status={data.get('status')}"
        )
        return True
    except Exception as e:
        logging.error(f"Erro ao atualizar disputa {dispute_number}: {e}")
        return False