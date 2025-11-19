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
from api_hapag.utils.storage import load_token
from api_hapag.repos.dispute_repository import upsert_disputa
import uuid


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


def enviar_disputa_hapag(
        invoice_id: int,
        invoice_number: str,
        shipment_number: str,
        disputed_amount: str,
        contact_email: str,
        dispute_text: str,
        charge_type: str = "WRONG_RELATION",
        dispute_type: str = "D16",
        disputed_currency: str = "USD"
) -> dict | None:
    """
    Envia uma nova disputa para a API Hapag-Lloyd e salva no banco.

    Args:
        invoice_id: ID da invoice no banco local
        invoice_number: Número da invoice Hapag
        shipment_number: Número do shipment/BL
        disputed_amount: Valor disputado
        contact_email: Email de contato
        dispute_text: Texto explicativo da disputa
        charge_type: Tipo de cobrança (padrão: "WRONG_RELATION")
        dispute_type: Código do tipo (padrão: "D16")
        disputed_currency: Moeda (padrão: "USD")

    Returns:
        dict com disputeNumber e status, ou None se erro
    """

    # Mapeamento de tipos
    charge_types = {
        "WRONG_RELATION": "Incorrect demurrage/detention charges or freetime application",
        "WRONG_AMOUNT": "Incorrect invoice amount",
        "WRONG_CHARGES": "Wrong charges applied",
        "DUPLICATE": "Duplicate invoice",
        "ALREADY_PAID": "Invoice already paid"
    }

    dispute_types = {
        "D16": "Incorrect origin timepending charges",
        "D17": "Incorrect destination timepending charges",
        "D01": "Incorrect freight charges",
        "D02": "Incorrect detention charges",
        "D03": "Incorrect demurrage charges",
        "D04": "Invoice already paid",
        "D05": "Duplicate invoice"
    }

    # Valida token
    token = load_token()
    if not token:
        logging.error("Token não encontrado")
        return None

    # Prepara requisição
    url = "https://dispute-form.api.hlag.cloud/api/dispute-form"

    headers = {
        "Authorization": f"Bearer {token}",
        "x-token": token,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    payload = {
        "invoiceDisputePositions": [
            {
                "id": str(uuid.uuid4()),
                "invoiceNumber": str(invoice_number),
                "shipmentNumber": str(shipment_number),
                "disputedCurrency": disputed_currency,
                "disputedAmount": str(disputed_amount)
            }
        ],
        "contactEmail": contact_email,
        "chargeType": charge_type,
        "chargeTypeLabel": charge_types.get(charge_type, charge_type),
        "disputeType": dispute_type,
        "disputeTypeLabel": dispute_types.get(dispute_type, dispute_type),
        "disputeText": dispute_text.strip(),
        "customerReference": contact_email,
        "attachmentIds": []
    }

    logging.info(f"Enviando disputa para invoice {invoice_number}...")

    # Envia para API
    r = fazer_requisicao_com_retry(
        url=url,
        headers=headers,
        metodo="POST",
        payload=payload,
        max_tentativas=3
    )

    if not r:
        logging.error("Falha ao enviar disputa")
        return None

    # Processa resposta
    if r.status_code == 200:
        data = r.json()
        dispute_number = data.get('disputeNumber')

        logging.info(f"Disputa {dispute_number} enviada com sucesso")

        # Salva no banco
        try:
            if dispute_number:
                disputa_id = upsert_disputa(
                    invoice_id=invoice_id,
                    dispute_number=dispute_number,
                    data={
                        'status': 'SUBMITTED',
                        'dispute_reason': dispute_type,
                        'amount': disputed_amount,
                        'currency': disputed_currency,
                        'ref': contact_email,
                        'allowSecondReview': False,
                        'disputeCreated': None
                    }
                )
                logging.info(f"Disputa salva no banco (id={disputa_id})")
        except Exception as e:
            logging.error(f"Erro ao salvar no banco: {e}")

        return {
            'disputeNumber': dispute_number,
            'status': data.get('status', 'SUBMITTED'),
            'message': 'Disputa criada com sucesso'
        }

    elif r.status_code == 400:
        logging.error(f"Dados invalidos (400): {r.text}")
        return None
    elif r.status_code == 409:
        logging.warning(f"Disputa ja existe (409): {r.text}")
        return None
    else:
        logging.error(f"Erro {r.status_code}: {r.text}")
        return None