import json
import jwt
from datetime import datetime
from typing import Dict, Optional
from pathlib import Path

from api_maersk.config.settings import TOKENS_FILE, CUSTOMER_CODE_MAPPING
from api_maersk.utils.logger import setup_logger

logger = setup_logger(__name__)


class TokenService:
    """Serviço para gerenciamento de tokens de autenticação."""

    def __init__(self, tokens_file: Path = TOKENS_FILE):
        self.tokens_file = tokens_file
        self._tokens_cache: Dict = {}

    def load_tokens(self) -> Dict:
        """Carrega tokens do arquivo."""
        if not self.tokens_file.exists():
            logger.warning(f"Arquivo de tokens não encontrado: {self.tokens_file}")
            return {}

        with open(self.tokens_file, "r", encoding="utf-8") as f:
            self._tokens_cache = json.load(f)

        logger.info(f"Carregados {len(self._tokens_cache)} tokens")
        return self._tokens_cache

    def save_tokens(self, tokens: Dict) -> None:
        """Salva tokens no arquivo."""
        self.tokens_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.tokens_file, "w", encoding="utf-8") as f:
            json.dump(tokens, f, indent=2, ensure_ascii=False)

        self._tokens_cache = tokens
        logger.info(f"Salvos {len(tokens)} tokens em {self.tokens_file}")

    def is_token_valid(self, token: str) -> bool:
        """Verifica se o token está válido (não expirado)."""
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            exp = decoded.get("exp")

            if not exp:
                logger.warning("Token sem campo 'exp'")
                return False

            expiration = datetime.fromtimestamp(exp)
            now = datetime.now()

            is_valid = expiration > now

            if is_valid:
                time_left = (expiration - now).total_seconds() / 3600
                logger.info(f"Token válido. Expira em {time_left:.1f} horas")
            else:
                logger.warning(f"Token expirado em {expiration}")

            return is_valid

        except jwt.DecodeError as e:
            logger.error(f"Erro ao decodificar token: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao validar token: {e}")
            return False

    def get_token(self, customer_code: str) -> Optional[str]:
        """
        Obtém token de um customer.

        Args:
            customer_code: Código do customer

        Returns:
            Token ou None se não encontrado
        """
        if not self._tokens_cache:
            self.load_tokens()

        if customer_code not in self._tokens_cache:
            logger.error(f"Customer {customer_code} não encontrado")
            return None

        token = self._tokens_cache[customer_code]["id_token"]
        return token
    def get_access_token(self, customer_code: str) -> Optional[str]:
        """
        Obtém o access_token de um customer (se existir no JSON).
        """
        if not self._tokens_cache:
            self.load_tokens()

        if customer_code not in self._tokens_cache:
            logger.error(f"Customer {customer_code} não encontrado")
            return None

        token = self._tokens_cache[customer_code].get("access_token")
        if not token:
            logger.warning(f"Access token não encontrado para {customer_code}")
        return token

    def update_token(self, customer_code: str, new_token: str) -> None:
        """Atualiza token de um customer específico."""
        if not self._tokens_cache:
            self.load_tokens()

        if customer_code in self._tokens_cache:
            self._tokens_cache[customer_code]["id_token"] = new_token
            self.save_tokens(self._tokens_cache)
            logger.info(f"Token atualizado para {customer_code}")
        else:
            logger.error(f"Customer {customer_code} não existe no cache")

    def get_api_customer_code(self, token_code: str) -> str:
        """Converte código do token para código da API."""
        return CUSTOMER_CODE_MAPPING.get(token_code, token_code)

    def get_valid_token(self, customer_code: str, auth_service=None) -> Optional[str]:
        """
        Obtém token válido, renovando automaticamente se expirado.

        Args:
            customer_code: Código do customer
            auth_service: AuthService para renovação (opcional)

        Returns:
            Token válido ou None
        """
        # 1. Pega token do arquivo
        token = self.get_token(customer_code)

        if not token:
            logger.error(f"Token não encontrado para {customer_code}")
            return None

        # 2. Testa se está válido
        if self.is_token_valid(token):
            # 5. Retorna token (se válido)
            return token

        # 3. Token expirado, precisa renovar
        logger.warning(f"Token expirado para {customer_code}")

        if not auth_service:
            logger.error("AuthService não fornecido. Não é possível renovar token automaticamente.")
            logger.info("Execute: py tests\\test_auth.py para renovar manualmente")
            return None

        # Renova token
        logger.info("Renovando token automaticamente...")
        new_token = auth_service.refresh_single_token(customer_code)

        if new_token:
            # 4. Salva no arquivo
            self.update_token(customer_code, new_token)
            # 5. Retorna token novo
            return new_token

        logger.error("Falha ao renovar token")
        return None

    def get_all_customers(self) -> Dict:
        """Retorna todos os customers disponíveis."""
        if not self._tokens_cache:
            self.load_tokens()
        return self._tokens_cache