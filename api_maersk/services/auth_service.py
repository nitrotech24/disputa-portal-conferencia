import time
from typing import Dict, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from api_maersk.config.settings import (
    MAERSK_USERNAME, MAERSK_PASSWORD, MAERSK_BASE_URL,
    SELENIUM_TIMEOUT, PAGE_LOAD_WAIT, TOKEN_CHECK_INTERVAL, MAX_TOKEN_CHECKS
)
from api_maersk.services.token_service import TokenService
from api_maersk.utils.logger import setup_logger

logger = setup_logger(__name__)


class AuthService:
    """Serviço para autenticação e renovação de tokens via Selenium."""

    def __init__(self, token_service: TokenService):
        self.token_service = token_service
        self.driver = None

    def _setup_driver(self) -> webdriver.Chrome:
        """Configura e retorna driver do Chrome."""
        logger.info("Configurando Chrome WebDriver...")

        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        try:
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
            return driver
        except Exception as e:
            logger.error(f"Erro Configurar Chrome WebDriver: {e}")
            raise e


    def _close_cookie_popup(self, driver: webdriver.Chrome) -> None:
        """Fecha popup de cookies se existir."""
        try:
            logger.info("Tentando fechar popup de cookies...")
            cookie_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Allow all')]"))
            )
            cookie_btn.click()
            logger.info("Popup fechado")
            time.sleep(2)
        except Exception:
            logger.info("Popup de cookies não encontrado")

    def _perform_login(self, driver: webdriver.Chrome) -> None:
        """Realiza o login no portal Maersk."""
        logger.info(f"Abrindo {MAERSK_BASE_URL}...")
        driver.get(MAERSK_BASE_URL)

        wait = WebDriverWait(driver, SELENIUM_TIMEOUT)
        time.sleep(PAGE_LOAD_WAIT)

        self._close_cookie_popup(driver)

        logger.info("Fazendo login...")
        login_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Login")))
        login_link.click()
        time.sleep(PAGE_LOAD_WAIT)

        user_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        user_field.send_keys(MAERSK_USERNAME)

        pwd_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        pwd_field.send_keys(MAERSK_PASSWORD)

        login_submit = wait.until(EC.element_to_be_clickable((By.ID, "login-submit-button")))
        login_submit.click()

        logger.info("Aguardando lista de customers...")
        time.sleep(5)

        WebDriverWait(driver, 10).until(
            EC.url_contains("/portaluser/select-customer")
        )
        time.sleep(PAGE_LOAD_WAIT)

    def _get_customers_list(self, driver: webdriver.Chrome) -> list:
        """Obtém lista de customers disponíveis."""
        logger.info("Coletando lista de customers...")

        script = """
        let customers = [];
        let mcTable = document.querySelector('mc-table');

        if (mcTable && mcTable.shadowRoot) {
            let cells = mcTable.shadowRoot.querySelectorAll('td[data-header-id="name"] div[role="cell"]');
            cells.forEach((cell, index) => {
                let nameSpan = cell.querySelector('span.prominent');
                let codeSpan = cell.querySelector('span.mds-font--small');
                if (nameSpan && codeSpan) {
                    customers.push({
                        index: index,
                        name: nameSpan.textContent.trim(),
                        code: codeSpan.textContent.trim()
                    });
                }
            });
        }
        return customers;
        """

        customers = driver.execute_script(script)
        logger.info(f"Encontrados {len(customers)} customers")

        return customers

    def _select_customer(self, driver: webdriver.Chrome, index: int) -> bool:
        """Seleciona um customer específico pelo índice."""
        script = f"""
        let mcTable = document.querySelector('mc-table');
        if (mcTable && mcTable.shadowRoot) {{
            let cells = mcTable.shadowRoot.querySelectorAll('td[data-header-id="name"] div[role="cell"]');
            if (cells[{index}]) {{
                cells[{index}].click();
                return true;
            }}
        }}
        return false;
        """

        return driver.execute_script(script)

    def _extract_token(self, driver: webdriver.Chrome) -> Optional[str]:
        """Extrai token do localStorage."""
        token_keys = ["[iam]id_token", "frJwt", "id_token"]

        for _ in range(MAX_TOKEN_CHECKS):
            for key in token_keys:
                token = driver.execute_script(f"return window.localStorage.getItem('{key}');")
                if token:
                    return token
            time.sleep(TOKEN_CHECK_INTERVAL)

        return None

    def refresh_all_tokens(self) -> Dict:
        """Renova tokens de todos os customers."""
        logger.info("=" * 80)
        logger.info("Iniciando renovação de tokens para todos os customers")
        logger.info("=" * 80)

        self.driver = self._setup_driver()
        all_tokens = {}

        try:
            self._perform_login(self.driver)
            customers = self._get_customers_list(self.driver)

            if not customers:
                logger.error("Nenhum customer encontrado!")
                return all_tokens

            for idx, customer in enumerate(customers):
                customer_name = customer['name']
                customer_code = customer['code']

                logger.info("")
                logger.info("=" * 80)
                logger.info(f"Customer {idx + 1}/{len(customers)}: {customer_name} ({customer_code})")
                logger.info("=" * 80)

                try:
                    if "/portaluser/select-customer" not in self.driver.current_url:
                        logger.info("Voltando para página de seleção...")
                        self.driver.get(f"{MAERSK_BASE_URL}/portaluser/select-customer")
                        time.sleep(PAGE_LOAD_WAIT)

                    if not self._select_customer(self.driver, idx):
                        logger.warning(f"Não conseguiu clicar no customer {customer_code}")
                        continue

                    logger.info("Customer selecionado, aguardando token...")
                    time.sleep(PAGE_LOAD_WAIT)

                    id_token = self._extract_token(self.driver)

                    if id_token:
                        all_tokens[customer_code] = {
                            "name": customer_name,
                            "code": customer_code,
                            "id_token": id_token
                        }
                        logger.info("Token capturado com sucesso!")
                    else:
                        logger.warning("Não conseguiu capturar token")

                except Exception as e:
                    logger.error(f"Erro ao processar customer: {e}")
                    continue

            if all_tokens:
                self.token_service.save_tokens(all_tokens)
                logger.info("")
                logger.info("=" * 80)
                logger.info(f"Processo concluído! {len(all_tokens)} tokens salvos")
                logger.info("=" * 80)

            return all_tokens

        finally:
            if self.driver:
                self.driver.quit()
                logger.info("WebDriver fechado")

    def refresh_single_token(self, customer_code: str) -> Optional[str]:
        """
        Renova token de um customer específico.
        Atualmente renova todos e retorna o específico.
        """
        logger.info(f"Renovando token para customer {customer_code}...")

        all_tokens = self.refresh_all_tokens()

        if customer_code in all_tokens:
            return all_tokens[customer_code]["id_token"]

        logger.error(f"Não foi possível renovar token para {customer_code}")
        return None