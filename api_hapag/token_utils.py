"""
token.py
Gerencia o ciclo de vida do XToken.
"""

import requests
import logging
from api_hapag.storage import load_token, save_token
from api_hapag.auth import login_and_get_token  # função que você já tem no auth.py

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def test_token(token: str) -> bool:
    """Verifica se o token ainda é válido chamando a API /disputes"""
    url = "https://dispute-overview.api.hlag.cloud/api/disputes?limit=1"
    headers = {
        "Authorization": f"Bearer {token}",
        "x-token": token,
        "Accept": "application/json"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.status_code == 200
    except requests.RequestException:
        return False


def get_valid_token() -> str | None:
    """
    Fluxo completo:
    1. Carrega token salvo
    2. Testa token
    3. Se inválido → gera novo via login
    4. Salva no arquivo
    5. Retorna token válido
    """
    token = load_token()
    if token:
        logging.info("Token carregado do arquivo. Testando...")
        if test_token(token):
            logging.info("Token ainda válido ✅")
            return token
        else:
            logging.warning("Token expirado ❌, gerando novo...")

    # Se não tinha ou expirou → gera novo
    new_token = login_and_get_token()
    if new_token:
        save_token(new_token)
        logging.info("Novo token salvo em xtoken.txt ✅")
        return new_token

    logging.error("Não foi possível obter token válido")
    return None

if __name__ == '__main__':
    get_valid_token()