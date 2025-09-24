"""
consulta.py
Consulta disputas na API da Hapag-Lloyd.
"""

import requests
import logging
from .auth import get_xtoken

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def consultar_disputa(dispute_id: int) -> dict | None:
    """
    Consulta uma disputa específica na API.
    - Se o token salvo estiver inválido/expirado, renova automaticamente.
    """
    def _request(token: str):
        """Função interna para chamar a API."""
        url = f"https://dispute-overview.api.hlag.cloud/api/disputes/{dispute_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "x-token": token,
            "Accept": "application/json",
            "Origin": "https://www.hapag-lloyd.com",
            "Referer": "https://www.hapag-lloyd.com/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        return requests.get(url, headers=headers, timeout=20)

    # 1ª tentativa: usa token atual
    token = get_xtoken()
    if not token:
        logging.error("Não foi possível obter token válido")
        return None

    logging.info(f"Consultando disputa {dispute_id}...")
    try:
        resp = _request(token)
        if resp.status_code == 200:
            logging.info("Consulta realizada com sucesso (token atual).")
            return resp.json()
        elif resp.status_code == 401:
            logging.warning("Token expirado/Inválido. Renovando...")
            new_token = get_xtoken(force_login=True)  # agora sim refaz login
            if new_token and new_token != token:
                resp = _request(new_token)
                if resp.status_code == 200:
                    logging.info("Consulta realizada com sucesso (token renovado).")
                    return resp.json()
                else:
                    logging.error(f"Erro {resp.status_code} mesmo após renovar token.")
            else:
                logging.error("Falha ao renovar token.")
        else:
            logging.error(f"Erro {resp.status_code}: {resp.text[:200]}")
    except requests.RequestException as e:
        logging.error(f"Erro de requisição: {e}")

    return None
