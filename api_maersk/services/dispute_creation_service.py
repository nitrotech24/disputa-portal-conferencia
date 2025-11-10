"""
Serviço de automação para criação de disputas no portal Maersk.
VERSÃO FINAL — Clique direto em <mc-button data-test="button-dispute">
"""

import time
from typing import Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException

from api_maersk.config.settings import (
    MAERSK_USERNAME,
    MAERSK_PASSWORD,
    MAERSK_BASE_URL,
    SELENIUM_TIMEOUT,
    PAGE_LOAD_WAIT
)
from api_maersk.services.token_service import TokenService
from api_maersk.utils.logger import setup_logger

logger = setup_logger(__name__)


class MaerskDisputeAutomation:
    """Automação completa para criação de disputas no portal Maersk."""

    def __init__(self, token_service: TokenService):
        self.token_service = token_service
        self.driver = None

    # =============================================================
    # SETUP E LOGIN
    # =============================================================
    def _setup_driver(self) -> webdriver.Chrome:
        logger.info("🔧 Configurando Chrome WebDriver...")
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        driver = webdriver.Chrome(options=chrome_options)
        logger.info("✅ Chrome WebDriver inicializado!")
        return driver

    def _close_cookie_popup(self, driver):
        try:
            logger.info("🍪 Tentando fechar popup de cookies...")
            cookie_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Allow all')]"))
            )
            cookie_btn.click()
            logger.info("✅ Popup de cookies fechado")
            time.sleep(2)
        except:
            logger.info("💡 Popup de cookies não encontrado")

    def _perform_login(self, driver):
        logger.info("🌐 Acessando site da Maersk...")
        driver.get(MAERSK_BASE_URL)
        time.sleep(PAGE_LOAD_WAIT)
        self._close_cookie_popup(driver)

        logger.info("🔐 Realizando login...")
        wait = WebDriverWait(driver, SELENIUM_TIMEOUT)

        login_link = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Login")))
        login_link.click()
        time.sleep(PAGE_LOAD_WAIT)

        user_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        user_field.send_keys(MAERSK_USERNAME)
        pwd_field = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        pwd_field.send_keys(MAERSK_PASSWORD)

        login_submit = wait.until(EC.element_to_be_clickable((By.ID, "login-submit-button")))
        login_submit.click()

        logger.info("⏳ Aguardando pós-login...")
        time.sleep(5)

        try:
            WebDriverWait(driver, 15).until(EC.url_contains("/portaluser/select-customer"))
            logger.info("✅ Página de seleção de customer detectada")
            return True
        except:
            logger.info("💡 Customer já selecionado automaticamente, continuando...")
            return False

    def _select_customer(self, driver, customer_code):
        logger.info(f"👤 Selecionando customer {customer_code}...")
        try:
            script = """
            let targetCode = arguments[0];
            let mcTable = document.querySelector('mc-table');
            if (mcTable && mcTable.shadowRoot) {
                let cells = mcTable.shadowRoot.querySelectorAll('td[data-header-id="name"] div[role="cell"]');
                for (let cell of cells) {
                    let codeSpan = cell.querySelector('span.mds-font--small');
                    if (codeSpan && codeSpan.textContent.trim() === targetCode) {
                        cell.click();
                        return true;
                    }
                }
            }
            return false;
            """
            success = driver.execute_script(script, customer_code)
            if success:
                time.sleep(5)
                logger.info("✅ Customer selecionado com sucesso!")
                return True
            logger.error(f"❌ Customer {customer_code} não encontrado")
            return False
        except Exception as e:
            logger.error(f"❌ Erro ao selecionar customer: {e}")
            return False

    # =============================================================
    # NAVEGAÇÃO E BUSCA
    # =============================================================
    def _navigate_to_myfinance(self, driver):
        logger.info("💰 Navegando para MyFinance...")
        driver.get(f"{MAERSK_BASE_URL}/myfinance")
        time.sleep(5)
        logger.info(f"✅ MyFinance carregado ({driver.current_url})")

    def _navigate_to_open_invoices(self, driver):
        logger.info("📋 Clicando na aba 'Open Invoices'...")
        try:
            open_invoices_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "mc-tab[data-test='openInvoices-tab']"))
            )
            open_invoices_tab.click()
            logger.info("✅ Aba 'Open Invoices' clicada!")
            time.sleep(3)
        except:
            logger.error("❌ Aba 'Open Invoices' não encontrada")

    def _search_invoice(self, driver: webdriver.Chrome, invoice_number: str) -> bool:
        """Busca a invoice e clica em 'Contestar'."""
        logger.info(f"🔍 Buscando invoice {invoice_number}...")

        try:
            search_box = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Fatura']"))
            )
            logger.info("✅ Campo de busca localizado!")

            driver.execute_script("arguments[0].focus(); arguments[0].value='';", search_box)
            search_box.send_keys(invoice_number)
            time.sleep(0.5)

            # Enter realista
            logger.info("🚀 Disparando evento Enter real...")
            driver.execute_script("""
                const input = arguments[0];
                input.focus();
                const evDown = new KeyboardEvent('keydown', {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true, composed:true});
                const evUp = new KeyboardEvent('keyup', {key:'Enter', code:'Enter', keyCode:13, which:13, bubbles:true, composed:true});
                input.dispatchEvent(evDown);
                input.dispatchEvent(evUp);
                input.blur();
            """, search_box)
            time.sleep(6)

            # Verifica se abriu página de busca
            current_url = driver.current_url
            if "/search?" not in current_url:
                logger.warning("⚠️ URL de busca não detectada — tentando Enter extra.")
                ActionChains(driver).move_to_element(search_box).send_keys(Keys.ENTER).perform()
                time.sleep(6)

            logger.info(f"🔎 URL atual: {current_url}")
            if "/search?" not in current_url:
                logger.error("❌ Busca não executada corretamente (URL não mudou).")
                driver.save_screenshot("debug_search_failed.png")
                return False

            # ----------------------------------------------------------------------
            # ETAPA FINAL: clicar diretamente no botão 'Contestar'
            # ----------------------------------------------------------------------
            logger.info("🧭 Procurando o botão 'Contestar' na página de resultados...")

            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-cy='table-wrapper']"))
                )
                time.sleep(2)

                driver.execute_script("window.scrollTo({top: document.body.scrollHeight/3, behavior: 'smooth'});")
                time.sleep(1)

                logger.info("🖱️ Gerando hover global pra revelar ações...")
                driver.execute_script("""
                    const evt = new MouseEvent('mousemove', {bubbles:true, composed:true, cancelable:true, view:window});
                    document.dispatchEvent(evt);
                """)

                dispute_btn = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "mc-button[data-test='button-dispute']"))
                )
                driver.execute_script("arguments[0].scrollIntoView({block:'center'});", dispute_btn)
                time.sleep(0.5)

                try:
                    logger.info("🖱️ Tentando clique direto no <mc-button>...")
                    dispute_btn.click()
                except Exception:
                    logger.info("⚙️  Tentando clique interno via shadowRoot...")
                    driver.execute_script("""
                        const host = arguments[0];
                        if (host.shadowRoot) {
                            const inner = host.shadowRoot.querySelector('button, [role=\"button\"]');
                            if (inner) inner.click();
                        } else { host.click(); }
                    """, dispute_btn)

                logger.info("✅ Clique em 'Contestar' executado com sucesso!")
                time.sleep(5)
                return True

            except Exception as e:
                logger.error(f"❌ Não foi possível clicar no botão 'Contestar': {e}")
                driver.save_screenshot("debug_contestar_not_clicked.png")
                return False

        except Exception as e:
            logger.error(f"❌ Erro geral na busca: {e}")
            driver.save_screenshot("debug_search_error.png")
            return False

    # =============================================================
    # EXECUÇÃO PRINCIPAL
    # =============================================================
    def create_dispute(self, customer_code, invoice_number, **kwargs) -> Dict:
        logger.info("=" * 80)
        logger.info("🚀 INICIANDO CRIAÇÃO DE DISPUTA")
        logger.info("=" * 80)
        logger.info(f"Customer: {customer_code}")
        logger.info(f"Invoice: {invoice_number}")
        logger.info("=" * 80)

        try:
            self.driver = self._setup_driver()
            needs_selection = self._perform_login(self.driver)
            if needs_selection:
                self._select_customer(self.driver, customer_code)

            self._navigate_to_myfinance(self.driver)
            self._navigate_to_open_invoices(self.driver)

            if not self._search_invoice(self.driver, invoice_number):
                return {"success": False, "error": "Falha ao buscar ou clicar em Contestar"}

            return {"success": True, "message": "Formulário de disputa aberto com sucesso"}

        except Exception as e:
            logger.error(f"❌ Erro geral na automação: {e}")
            return {"success": False, "error": str(e)}

        finally:
            if self.driver:
                logger.info("🔄 Mantendo navegador aberto 10s para inspeção...")
                time.sleep(10)
                self.driver.quit()
                logger.info("✅ Navegador fechado com sucesso.")