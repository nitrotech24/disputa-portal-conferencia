"""
Automação de criação de disputas no portal Maersk.
Navegação direta via URL
"""

import time
from typing import Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from api_maersk.config.settings import (
    MAERSK_USERNAME,
    MAERSK_PASSWORD,
    MAERSK_BASE_URL,
    SELENIUM_TIMEOUT,
    PAGE_LOAD_WAIT
)
from api_maersk.services.token_service import TokenService
from api_maersk.utils.logger import setup_logger
from selenium.webdriver.common.keys import Keys

logger = setup_logger(__name__)


class MaerskDisputeAutomation:
    """Automação para criação de disputas no portal Maersk."""

    def __init__(self, token_service: TokenService):
        self.token_service = token_service
        self.driver = None

    def _setup_driver(self) -> webdriver.Chrome:
        logger.info("Configurando Chrome WebDriver...")
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        driver = webdriver.Chrome(options=options)
        logger.info("Chrome WebDriver inicializado com sucesso")
        return driver

    def _perform_login(self, driver):
        logger.info("Acessando portal Maersk...")
        driver.get(MAERSK_BASE_URL)
        time.sleep(PAGE_LOAD_WAIT)

        try:
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(),'Allow all')]"))
            )
            btn.click()
            logger.info("Popup de cookies fechado")
        except:
            logger.info("Nenhum popup de cookies detectado")

        logger.info("Realizando login...")
        wait = WebDriverWait(driver, SELENIUM_TIMEOUT)
        wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Login"))).click()
        time.sleep(PAGE_LOAD_WAIT)

        user = wait.until(EC.presence_of_element_located((By.NAME, "username")))
        pwd = wait.until(EC.presence_of_element_located((By.NAME, "password")))
        user.send_keys(MAERSK_USERNAME)
        pwd.send_keys(MAERSK_PASSWORD)
        wait.until(EC.element_to_be_clickable((By.ID, "login-submit-button"))).click()

        time.sleep(5)
        try:
            WebDriverWait(driver, 15).until(EC.url_contains("/portaluser/select-customer"))
            logger.info("Página de seleção de customer detectada")
            return True
        except:
            logger.info("Customer já selecionado automaticamente")
            return False

    def _select_customer(self, driver, customer_code):
        logger.info(f"Selecionando customer {customer_code}...")
        script = """
        const code = arguments[0];
        const mcTable = document.querySelector('mc-table');
        if (!mcTable || !mcTable.shadowRoot) return false;
        const cells = mcTable.shadowRoot.querySelectorAll('td[data-header-id="name"] div[role="cell"]');
        for (let c of cells) {
            const span = c.querySelector('span.mds-font--small');
            if (span && span.textContent.trim() === code) { c.click(); return true; }
        }
        return false;
        """
        success = driver.execute_script(script, customer_code)
        if success:
            time.sleep(4)
            logger.info("Customer selecionado com sucesso")
            return True
        else:
            logger.warning("Customer não encontrado")
            return False

    def create_dispute(self, customer_code, invoice_number, **kwargs) -> Dict:
        logger.info("=" * 80)
        logger.info("AUTOMAÇÃO MAERSK - VERSÃO ULTRA SIMPLIFICADA")
        logger.info("=" * 80)

        try:
            self.driver = self._setup_driver()

            # Login
            needs_selection = self._perform_login(self.driver)
            if needs_selection:
                if not self._select_customer(self.driver, customer_code):
                    return {"success": False, "error": "Falha ao selecionar customer"}

            # Navegação direta para a página de criar disputa
            logger.info(f"Navegando para página de disputa da invoice {invoice_number}...")
            dispute_url = "https://www.maersk.com/myfinance/"
            self.driver.get(dispute_url)

            # Aguarda o carregamento da página
            logger.info("Aguardando página de disputa carregar...")
            time.sleep(8)

            # Aguarda o campo de busca estar presente
            search_input_script = """
                // Tenta primeiro sem Shadow DOM
                let input = document.querySelector('input[placeholder*="Search by B/L"]');

                // Se não encontrar, procura em Shadow DOMs
                if (!input) {
                    const allElements = document.querySelectorAll('*');
                    for (let el of allElements) {
                        if (el.shadowRoot) {
                            input = el.shadowRoot.querySelector('input[placeholder*="Search by B/L"]');
                            if (input) break;
                        }
                    }
                }

                return input;
                """
            search_input = self.driver.execute_script(search_input_script)
            search_input.send_keys(invoice_number)
            search_input.send_keys(Keys.RETURN)
            time.sleep(5)

            # Clica no botão Dispute
            logger.info("Procurando botão Dispute...")

            logger.info("Reduzindo janela para clicar no botão...")
            self.driver.set_window_size(400, 720)
            time.sleep(1)

            click_dispute_script = """
            // Procura o botão mc-button com data-test="button-dispute"
            const button = document.querySelector('mc-button[data-test="button-dispute"]');

            if (!button) {
                return {success: false, error: 'Botão Dispute não encontrado no DOM'};
            }

            // Tenta clicar direto no mc-button
            button.click();

            // Se não funcionar, tenta no shadowRoot
            if (button.shadowRoot) {
                const innerButton = button.shadowRoot.querySelector('button');
                if (innerButton) {
                    innerButton.click();
                    return {success: true, message: 'Clicado no botão interno do Shadow DOM'};
                }
            }

            return {success: true, message: 'Clicado no mc-button'};
            """
            result = self.driver.execute_script(click_dispute_script)

            if not result.get('success'):
                logger.error(f"Erro ao clicar no botão Dispute: {result.get('error')}")
                self.driver.save_screenshot("debug_botao_dispute_nao_encontrado.png")
                return {"success": False, "error": result.get('error')}

            # Volta ao tamanho original
            logger.info("Restaurando tamanho original da janela...")
            self.driver.maximize_window()
            time.sleep(1)

            # Aguarda o carregamento da página
            logger.info("Aguardando página de disputa carregar...")
            time.sleep(8)

            # Verifica se a URL foi redirecionada corretamente
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.url_contains("/disputes/create")
                )
                logger.info("Página de criar disputa aberta com sucesso")
            except:
                logger.error("Falha ao redirecionar para página de disputa")
                self.driver.save_screenshot("debug_nao_redirecionou.png")
                return {"success": False, "error": "Não chegou na página de disputa"}

            # Verifica se a invoice foi carregada na página
            logger.info(f"Verificando se invoice {invoice_number} foi carregada...")
            time.sleep(3)

            invoice_found = self.driver.execute_script("""
                const invoiceNum = arguments[0];
                const text = document.body.textContent;
                return text.includes(invoiceNum);
            """, invoice_number)

            if invoice_found:
                logger.info(f"Invoice {invoice_number} encontrada na página")
            else:
                logger.warning(f"Invoice {invoice_number} não apareceu na página")

            select_script = """
            // Procura o select com aria-label
            let select = document.querySelector('select[aria-label="Dispute reason"]');

            // Se não encontrar, procura por id
            if (!select) {
                select = document.getElementById('select');
            }

            // Se não encontrar, procura em Shadow DOMs
            if (!select) {
                const allElements = document.querySelectorAll('*');
                for (let el of allElements) {
                    if (el.shadowRoot) {
                        select = el.shadowRoot.querySelector('select[aria-label="Dispute reason"]');
                        if (select) break;
                    }
                }
            }

            if (!select) return {success: false, error: 'Select não encontrado'};

            // Seleciona o valor
            select.value = arguments[0];
            select.dispatchEvent(new Event('change', { bubbles: true }));
            select.dispatchEvent(new Event('input', { bubbles: true }));

            return {success: true, value: select.value};
            """
            self.driver.execute_script(select_script, "0001")

            checkbox_script = """
            const label = document.querySelector('label[for="00000001-checkbox"]');
            if (label) {
                label.click();
                return {success: true};
            }
            return {success: false, error: 'Checkbox não encontrado'};
            """

            self.driver.execute_script(checkbox_script)

            select_category_script = """
            const category = arguments[0];

            // Procura TODOS os selects de Dispute category
            const allSelects = [];

            // Busca no DOM normal
            document.querySelectorAll('select[aria-label="Dispute category"]').forEach(s => allSelects.push(s));

            // Busca em Shadow DOMs
            document.querySelectorAll('*').forEach(el => {
                if (el.shadowRoot) {
                    el.shadowRoot.querySelectorAll('select[aria-label="Dispute category"]').forEach(s => allSelects.push(s));
                }
            });

            if (allSelects.length === 0) {
                return {success: false, error: 'Nenhum select encontrado'};
            }

            // Preenche TODOS os selects encontrados
            allSelects.forEach(select => {
                if (select.disabled) {
                    select.disabled = false;
                }
                select.value = category;
                select.dispatchEvent(new Event('change', { bubbles: true }));
                select.dispatchEvent(new Event('input', { bubbles: true }));
            });

            return {success: true, selectsFound: allSelects.length};
            """

            result = self.driver.execute_script(select_category_script, "rateNotAsPerContractualAgreement")

            logger.info(f"Dispute Category preenchida em {result.get('selectsFound')} campos")
            time.sleep(1)

            logger.info("Preenchendo Expected Amount...")

            # Acessa o input via Shadow DOM
            input_element = self.driver.execute_script("""
                const mcInput = document.getElementById('00000001-expectedAmount');
                if (mcInput && mcInput.shadowRoot) {
                    const input = mcInput.shadowRoot.querySelector('input[type="text"]');
                    if (input) {
                        input.disabled = false;
                        input.readOnly = false;
                        return input;
                    }
                }
                return null;
            """)

            if not input_element:
                logger.error("Input Expected Amount não encontrado")
                self.driver.save_screenshot("debug_input_not_found.png")
                return {"success": False, "error": "Input não encontrado"}

            # Clica, limpa, digita e pressiona TAB
            input_element.click()
            time.sleep(0.5)
            input_element.clear()
            input_element.send_keys("1500")
            input_element.send_keys(Keys.TAB)

            logger.info("Expected Amount preenchido: 1500")
            time.sleep(2)

            logger.info("Preenchendo descrição da disputa...")

            # Busca o textarea via Shadow DOM
            textarea_element = self.driver.execute_script("""
                let textarea = document.querySelector('textarea[name="noteDescription"]');

                if (!textarea) {
                    const mcTextarea = document.querySelector('mc-textarea[name="noteDescription"]');
                    if (mcTextarea && mcTextarea.shadowRoot) {
                        textarea = mcTextarea.shadowRoot.querySelector('textarea');
                    }
                }

                return textarea;
            """)

            if not textarea_element:
                logger.error("Textarea não encontrado")
                self.driver.save_screenshot("debug_textarea_not_found.png")
                return {"success": False, "error": "Textarea não encontrado"}

            # Usa Selenium para preencher
            textarea_element.click()
            time.sleep(0.3)
            textarea_element.clear()
            textarea_element.send_keys("TESTE - Disputa criada via automação")
            textarea_element.send_keys(Keys.TAB)

            logger.info("Descrição preenchida")
            time.sleep(1)

            logger.info("Preenchendo informações de contato...")

            contact_name = "Fernando"
            contact_email = "fernando.conceicao@nitro.com.br"
            contact_phone = "+55 11 99999-9999"

            # Preenche Name
            try:
                name_input = self.driver.execute_script("""
                    const mcInput = document.getElementById('contactPerson');
                    if (mcInput && mcInput.shadowRoot) {
                        return mcInput.shadowRoot.querySelector('input[type="text"]');
                    }
                    return null;
                """)
                if name_input:
                    name_input.clear()
                    name_input.send_keys(contact_name)
                    name_input.send_keys(Keys.TAB)
                    logger.info(f"Name preenchido: {contact_name}")
            except Exception as e:
                logger.warning(f"Erro ao preencher Name: {e}")

            time.sleep(0.5)

            # Preenche Email
            try:
                email_input = self.driver.execute_script("""
                    const mcInput = document.getElementById('contactEmail');
                    if (mcInput && mcInput.shadowRoot) {
                        return mcInput.shadowRoot.querySelector('input[type="text"]');
                    }
                    return null;
                """)
                if email_input:
                    email_input.clear()
                    email_input.send_keys(contact_email)
                    email_input.send_keys(Keys.TAB)
                    logger.info(f"Email preenchido: {contact_email}")
            except Exception as e:
                logger.warning(f"Erro ao preencher Email: {e}")

            time.sleep(0.5)

            # Preenche Contact Number
            try:
                phone_input = self.driver.execute_script("""
                    const mcInput = document.getElementById('contactTelNumber');
                    if (mcInput && mcInput.shadowRoot) {
                        return mcInput.shadowRoot.querySelector('input[type="text"]');
                    }
                    return null;
                """)
                if phone_input:
                    phone_input.clear()
                    phone_input.send_keys(contact_phone)
                    phone_input.send_keys(Keys.TAB)
                    logger.info(f"Contact Number preenchido: {contact_phone}")
                else:
                    logger.error("Input de Contact Number não encontrado")
                    self.driver.save_screenshot("debug_phone_not_found.png")
            except Exception as e:
                logger.error(f"Erro ao preencher Contact Number: {e}")
                self.driver.save_screenshot("debug_phone_error.png")

            time.sleep(1)
            logger.info("Informações de contato preenchidas")

            logger.info("Clicando no botão Continue...")

            click_continue_script = """
            // Busca o mc-button com label="Continue"
            const mcButton = document.querySelector('mc-button[label="Continue"]');

            if (!mcButton) {
                return {success: false, error: 'Botão Continue não encontrado'};
            }

            // Tenta clicar no mc-button primeiro
            mcButton.click();

            // Se tiver Shadow DOM, clica no botão interno também
            if (mcButton.shadowRoot) {
                const innerButton = mcButton.shadowRoot.querySelector('button');
                if (innerButton) {
                    innerButton.click();
                    return {success: true, method: 'shadow-dom-button'};
                }
            }

            return {success: true, method: 'mc-button'};
            """

            result = self.driver.execute_script(click_continue_script)

            if not result.get('success'):
                logger.error(f"Erro ao clicar no botão Continue: {result.get('error')}")
                self.driver.save_screenshot("debug_erro_continue_button.png")
                return {"success": False, "error": result.get('error')}

            logger.info(f"Botão Continue clicado (método: {result.get('method')})")

            # Aguarda o redirecionamento/modal
            time.sleep(5)

            # Verifica se foi para próxima página
            logger.info(f"URL atual após Continue: {self.driver.current_url}")
            self.driver.save_screenshot("debug_apos_continue.png")
            logger.info("Screenshot salvo: debug_apos_continue.png")

            # Captura screenshot da página final
            self.driver.save_screenshot("debug_pagina_disputa.png")
            logger.info("Screenshot salvo: debug_pagina_disputa.png")

            logger.info("Página de disputa aberta com sucesso")

            # ============================================================
            # CÓDIGO PARA CLICAR NO CREATE DISPUTE (COMENTADO)
            # ============================================================
            # # Aguarda o modal de confirmação carregar
            # logger.info("Aguardando modal de confirmação...")
            # time.sleep(5)
            #
            # # Clica no botão "Create dispute"
            # logger.info("Clicando no botão Create Dispute...")
            #
            # click_create_dispute_script = """
            # // Procura o footer com os actions
            # const footer = document.querySelector('footer#actions.mdc-dialog__actions');
            #
            # if (!footer) {
            #     return {success: false, error: 'Footer não encontrado'};
            # }
            #
            # // Procura o slot primaryAction
            # const primarySlot = footer.querySelector('slot[name="primaryAction"]');
            #
            # if (!primarySlot) {
            #     return {success: false, error: 'Slot primaryAction não encontrado'};
            # }
            #
            # // Pega o botão atribuído ao slot
            # const assignedElements = primarySlot.assignedElements();
            #
            # if (assignedElements.length === 0) {
            #     return {success: false, error: 'Nenhum botão no slot'};
            # }
            #
            # // Clica no botão
            # const button = assignedElements[0];
            # button.click();
            #
            # // Se tiver Shadow DOM, clica no botão interno também
            # if (button.shadowRoot) {
            #     const innerButton = button.shadowRoot.querySelector('button');
            #     if (innerButton) {
            #         innerButton.click();
            #     }
            # }
            #
            # return {success: true};
            # """
            #
            # result = self.driver.execute_script(click_create_dispute_script)
            #
            # if not result.get('success'):
            #     logger.error(f"Erro ao clicar no botão: {result.get('error')}")
            #     self.driver.save_screenshot("debug_botao_create_erro.png")
            #     return {"success": False, "error": result.get('error')}
            #
            # logger.info("Botão Create Dispute clicado")
            #
            # # Aguarda processamento
            # time.sleep(5)
            #
            # # Screenshot final
            # self.driver.save_screenshot("debug_final.png")
            # logger.info("Screenshot final salvo: debug_final.png")
            #
            # logger.info("Disputa criada com sucesso!")
            # ============================================================

            return {
                "success": True,
                "message": "Página de disputa aberta com sucesso",
                "invoice_found": invoice_found,
                "url": self.driver.current_url
            }

        except Exception as e:
            logger.exception("Erro inesperado durante execução")
            self.driver.save_screenshot("debug_erro.png")
            return {"success": False, "error": str(e)}
        finally:
            if self.driver:
                logger.info("Encerrando navegador...")
                time.sleep(20)
                self.driver.quit()
                logger.info("Navegador fechado")