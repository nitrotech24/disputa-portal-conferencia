import requests
from typing import Dict, List, Optional
import json

from config.settings import API_BASE_URL, CONSUMER_KEY, CARRIER_CODE
from services.token_service import TokenService
from services.auth_service import AuthService
from utils.logger import setup_logger

logger = setup_logger(__name__)


class DisputeService:
    """Serviço para gerenciamento de disputas e invoices via API Maersk."""

    def __init__(self, token_service: TokenService, auth_service: AuthService):
        self.token_service = token_service
        self.auth_service = auth_service

    # -------------------------
    # Internos
    # -------------------------
    def _build_headers(self, token: str, customer_code: str, accept: str) -> Dict:
        """Monta headers para requisições à API Maersk."""
        return {
            "Authorization": f"Bearer {token}",
            "consumer-key": CONSUMER_KEY,
            "carrier-code": CARRIER_CODE.lower(),  # sempre minúsculo
            "customer-code": customer_code,  # incluir sempre
            "accept": accept,
            "Origin": "https://www.maersk.com",
            "Referer": "https://www.maersk.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
            ),
        }

    def _call_api(
            self,
            endpoint: str,
            token: str,
            customer_code: str,
            accept: str = "application/vnd.ohp.dispute.v1+json",
    ) -> Optional[Dict]:
        """Executa chamada GET na API Maersk."""
        url = f"{API_BASE_URL}{endpoint}"
        headers = self._build_headers(token, customer_code, accept)

        try:
            response = requests.get(url, headers=headers, timeout=30)
            logger.info(f"GET {endpoint} - Status: {response.status_code}")

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.warning("Token inválido (401). Precisa renovar!")
                return None
            else:
                logger.error(f"Erro {response.status_code}: {response.text[:200]}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
            return None

    def _get_token_and_api_code(self, customer_code: str) -> Optional[tuple]:
        """Centraliza a obtenção de api_code + token válido."""
        api_code = self.token_service.get_api_customer_code(customer_code)
        token = self.token_service.get_valid_token(customer_code, auth_service=self.auth_service)
        if not token:
            logger.error(f"Não foi possível obter token válido para {customer_code}")
            return None
        return api_code, token

    # -------------------------
    # Disputes
    # -------------------------
    def get_dispute_details(self, dispute_id: str, customer_code: str) -> Optional[Dict]:
        """Obtém detalhes de uma disputa específica."""
        result = self._get_token_and_api_code(customer_code)
        if not result:
            return None
        api_code, token = result

        logger.info(f"Consultando disputa {dispute_id} para {api_code}")
        return self._call_api(
            f"/disputes-external/api/dispute/{dispute_id}",
            token,
            api_code,
            "application/vnd.ohp.dispute.v1+json",
        )

    def get_dispute_comments(
            self, dispute_id: str, customer_code: str, limit: int = 10, page: int = 0
    ) -> Optional[List[Dict]]:
        """Obtém comentários de uma disputa."""
        result = self._get_token_and_api_code(customer_code)
        if not result:
            return None
        api_code, token = result

        logger.info(f"Consultando comentários da disputa {dispute_id}")
        data = self._call_api(
            f"/disputes-external/api/dispute/{dispute_id}/comment?limit={limit}&page={page}",
            token,
            api_code,
        )
        return data.get("comments", []) if data else None

    def get_dispute_attachments(self, dispute_id: str, customer_code: str) -> Optional[List[Dict]]:
        """Obtém anexos de uma disputa."""
        result = self._get_token_and_api_code(customer_code)
        if not result:
            return None
        api_code, token = result

        logger.info(f"Consultando anexos da disputa {dispute_id}")
        data = self._call_api(
            f"/disputes-external/api/dispute/attachment/{dispute_id}",
            token,
            api_code,
            "application/vnd.ohp.dispute.v2+json",
        )
        return data.get("attachments", []) if data else None

    def get_disputes_by_invoice(self, invoice_number: str, customer_code: str) -> List[Dict]:
        """
        Busca disputas relacionadas a uma invoice.
        Agora usa o endpoint oficial (POST /dispute/search/filter).
        """
        return self.search_disputes_by_invoice(invoice_number, customer_code)

    def search_disputes_by_invoice(self, invoice_number: str, customer_code: str) -> List[Dict]:
        """
        Busca disputas por invoice usando o endpoint de filtro (POST).
        Retorna lista de disputas (cada disputa é um dict).
        """
        result = self._get_token_and_api_code(customer_code)
        if not result:
            return []
        api_code, token = result

        url = f"{API_BASE_URL}/disputes-external/api/dispute/search/filter"

        headers = {
            "Authorization": f"Bearer {token}",
            "consumer-key": CONSUMER_KEY,
            "carrier-code": CARRIER_CODE.lower(),
            "customer-code": api_code,
            "content-type": "application/json",
            "accept": "application/vnd.ohp.dispute.v1+json",
            "Origin": "https://www.maersk.com",
            "Referer": "https://www.maersk.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0.0.0 Safari/537.36"
            ),
        }

        payload = {
            "object_id": "disputes-view",
            "search": None,  # Mude de "" para None
            "filters": [
                {
                    "exclude": False,
                    "updatable": True,
                    "property_id": "invoiceNumber",
                    "filterName": "Invoice number",
                    "values": [invoice_number],
                }
            ],
        }

        try:
            logger.info(f"Payload enviado: {json.dumps(payload, indent=2)}")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            logger.info(f"POST {url} - Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.info(f"Resposta: {json.dumps(data, indent=2)[:500]}")
                disputes = data.get("search_records", [])  # MUDE AQUI: disputes → search_records
                logger.info(f"Encontradas {len(disputes)} disputas")
                return disputes
            elif response.status_code == 401:
                logger.warning("Token inválido (401). Precisa renovar!")
                return []
            else:
                logger.error(f"Erro {response.status_code}: {response.text[:200]}")
                return []

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição: {e}")
            return []

    def list_all_disputes(self, customer_code: str, page_size: int = 337) -> List[Dict]:
        """
        Lista TODAS as disputas do customer (sem filtros).
        Retorna lista de disputas com invoiceNumber e ohpDisputeId.
        """
        result = self._get_token_and_api_code(customer_code)
        if not result:
            return []
        api_code, token = result

        url = f"{API_BASE_URL}/disputes-external/api/dispute/search/filter?page_no=0&page_size={page_size}"

        headers = {
            "Authorization": f"Bearer {token}",
            "consumer-key": CONSUMER_KEY,
            "carrier-code": CARRIER_CODE.lower(),
            "customer-code": api_code,
            "content-type": "application/json",
            "accept": "application/vnd.ohp.dispute.v1+json",
            "Origin": "https://www.maersk.com",
            "Referer": "https://www.maersk.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
            ),
        }

        payload = {
            "object_id": "disputes-view",
            "filters": [],  # SEM FILTROS - lista todas
            "sort_by": "ohpDisputeId",
            "sort_order": "DESC",
            "search": None
        }

        try:
            logger.info(f"Payload: {json.dumps(payload, indent=2)}")
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            logger.info(f"POST {url} - Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.info(f"Resposta: {json.dumps(data, indent=2)[:500]}")
                disputes = data.get("search_records", [])
                logger.info(f"Encontradas {len(disputes)} disputas")
                return disputes
            else:
                logger.error(f"Erro {response.status_code}: {response.text[:200]}")
                return []

        except Exception as e:
            logger.error(f"Erro: {e}")
            return []
    # -------------------------
    # Invoices
    # -------------------------
    def get_invoice_info(
            self, invoice_number: str, customer_code: str, invoice_type: str = "OPEN"
    ) -> Optional[Dict]:
        """Consulta endpoint /invoices."""
        result = self._get_token_and_api_code(customer_code)
        if not result:
            return None
        api_code, token = result

        endpoint = (
            f"/invoices?searchType=INV_NOS"
            f"&ids={invoice_number}"
            f"&customerCodeCMD={api_code}"
            f"&carrierCode={CARRIER_CODE}"
            f"&invoiceType={invoice_type}"
            f"&isSelected=true"
            f"&isCreditCountry=true"
        )

        url = f"{API_BASE_URL}{endpoint}"

        # USA CONSUMER-KEY DIFERENTE PARA /invoices
        headers = {
            "Authorization": f"Bearer {token}",
            "consumer-key": "SqsiObucFhI8PTFlsakGygUALAVLQ0yT",  # CONSUMER-KEY ESPECÍFICO
            "accept": "*/*",
            "Origin": "https://www.maersk.com",
            "Referer": "https://www.maersk.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
            ),
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            logger.info(f"GET {endpoint} - Status: {response.status_code}")

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Erro {response.status_code}: {response.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Erro: {e}")
            return None

    def check_invoice_has_dispute(self, invoice_number: str, customer_code: str) -> Dict:
        """
        Verifica se uma invoice tem disputa.

        Returns:
            {
                "has_dispute": True/False,
                "invoice_data": {...},
                "disputes": [...]  # se encontrar
            }
        """
        result = {}

        # 1. Busca a invoice
        invoice_data = self.get_invoice_info(invoice_number, customer_code, invoice_type="OPEN")

        if not invoice_data or not invoice_data.get("invoices"):
            logger.warning(f"Invoice {invoice_number} não encontrada")
            return {"has_dispute": False, "invoice_data": None, "disputes": []}

        invoice = invoice_data["invoices"][0]
        result["invoice_data"] = invoice

        # 2. Verifica se tem indicação de disputa nos campos da invoice
        has_dispute = invoice.get("isDisputable") == False  # Se False, pode ter disputa existente

        result["has_dispute"] = has_dispute
        result["disputes"] = []

        logger.info(f"Invoice {invoice_number}: has_dispute={has_dispute}")

        return result