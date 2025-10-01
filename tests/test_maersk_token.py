import os
import pytest
from api_maersk import token_utils

def test_maersk_token_file_exists():
    """
    Verifica se o arquivo de token foi gerado no artifacts/.
    Pré-requisito: rodar login_maersk.py antes.
    """
    token_path = os.path.join("artifacts", "maersk_token.json")
    assert os.path.exists(token_path), (
        "❌ Arquivo de token não encontrado. Rode api_maersk/login_maersk.py antes de testar."
    )

def test_maersk_token_is_valid():
    """
    Testa se o token salvo é válido.
    Obs: usa token_utils.test_token() → ainda precisa de um endpoint real da Maersk.
    """
    token = token_utils.get_valid_token()
    assert token is not None, "❌ Nenhum token retornado"
    assert isinstance(token, str), "❌ Token não é string"
    assert len(token) > 30, "❌ Token muito curto, pode estar inválido"
    print(f"✅ Token válido carregado: {token[:40]}...")
