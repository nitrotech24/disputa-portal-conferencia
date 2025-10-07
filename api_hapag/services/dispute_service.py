"""
dispute_service.py
Serviço para consultar disputas na API da Hapag-Lloyd.
MELHORADO: Retry automático e validação robusta
"""

import logging
import requests
import time
from typing import Optional
from api_hapag.services.token_service import get_valid_token
from api_hapag.repos.dispute_repository import update_disputa_completa

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def fazer_requisicao_com_retry(url: str, headers: dict, max_tentativas: int = 3, metodo: str = "GET",
                               payload: dict = None) -> requests.Response | None:
    """
    Faz requisição HTTP com retry automático

    Args:
        url: URL da API
        headers: Headers da requisição
        max_tentativas: Número máximo de tentativas
        metodo: GET ou POST
        payload: Dados para POST (opcional)

    Returns:
        Response ou None se todas as tentativas falharem
    """
    for tentativa in range(1, max_tentativas + 1):
        try:
            if metodo == "POST":
                r = requests.post(url, headers=headers, json=payload, timeout=20)
            else:
                r = requests.get(url, headers=headers, timeout=20)

            # Se for 200 ou 404, retorna (não precisa retry)
            if r.status_code in [200, 404]:
                return r

            # Se for 401 (token inválido), não adianta retry
            if r.status_code == 401:
                logging.error(f"Token inválido (401). Renovação necessária.")
                return None

            # Para outros erros, tenta novamente
            logging.warning(f"Tentativa {tentativa}/{max_tentativas} falhou: {r.status_code}")

            if tentativa < max_tentativas:
                tempo_espera = 2 ** tentativa  # Backoff exponencial: 2, 4, 8 segundos
                logging.info(f"Aguardando {tempo_espera}s antes de tentar novamente...")
                time.sleep(tempo_espera)

        except requests.RequestException as e:
            logging.error(f"Erro na requisição (tentativa {tentativa}/{max_tentativas}): {e}")
            if tentativa < max_tentativas:
                time.sleep(2 ** tentativa)

    logging.error(f"Todas as {max_tentativas} tentativas falharam")
    return None


def consultar_disputa(dispute_number: int) -> dict | None:
    """
    Consulta detalhes completos de uma disputa específica na API.
    MELHORADO: Com retry automático

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

    r = fazer_requisicao_com_retry(url, headers)

    if not r:
        return None

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
            'dispute_reason': data.get('dispute_reason') or data.get('disputeReason'),
            'amount': data.get('amount') or data.get('disputedAmount'),
            'currency': data.get('currency'),
            'ref': data.get('ref') or data.get('reference'),
            'allowSecondReview': data.get('allowSecondReview'),
            'disputeCreated': data.get('disputeCreated') or data.get('createdDate'),
            'invoiceNumber': data.get('invoiceNumber'),
            'disputeNumber': data.get('disputeNumber') or dispute_number
        }
    elif r.status_code == 404:
        logging.warning(f"Disputa {dispute_number} não encontrada")
        return None
    else:
        logging.error(f"Erro {r.status_code}: {r.text}")
        return None


def consultar_invoice(invoice_number: str) -> list | None:
    """
    Consulta disputas relacionadas a uma invoice.
    Retorna lista de disputas com todos os campos normalizados.
    MELHORADO: Com retry e melhor normalização

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

    # Tenta GET primeiro
    r = fazer_requisicao_com_retry(f"{url}?invoiceNumber={invoice_number}", headers)

    if r and r.status_code == 200:
        logging.info(f"Invoice {invoice_number}: disputas encontradas via GET")
        return _normalizar_disputas(r.json())

    # Se não encontrou via GET, tenta POST
    logging.info(f"Invoice {invoice_number}: tentando POST...")
    payload = {"invoiceNumber": invoice_number}
    r = fazer_requisicao_com_retry(url, headers, metodo="POST", payload=payload)

    if r and r.status_code == 200:
        logging.info(f"Invoice {invoice_number}: disputas encontradas via POST")
        return _normalizar_disputas(r.json())

    logging.warning(f"Invoice {invoice_number}: nenhuma disputa encontrada")
    return None


def _normalizar_disputas(data: list | dict) -> list:
    """
    Normaliza resposta da API para formato padronizado.
    A API pode retornar lista ou objeto único.
    MELHORADO: Mais campos alternativos
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
            'dispute_reason': d.get('dispute_reason') or d.get('disputeReason'),
            'amount': d.get('amount') or d.get('disputedAmount'),
            'currency': d.get('currency'),
            'ref': d.get('ref') or d.get('reference'),
            'allowSecondReview': d.get('allowSecondReview'),
            'disputeCreated': d.get('disputeCreated') or d.get('createdDate'),
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