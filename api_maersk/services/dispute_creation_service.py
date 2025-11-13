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
            #dispute_url = f"{MAERSK_BASE_URL}/disputes/create?invoice={invoice_number}"
            dispute_url ="https://www.maersk.com/myfinance/"
            self.driver.get(dispute_url)

            #wait = WebDriverWait(self.driver, SELENIUM_TIMEOUT)

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
            time.sleep(1)  # Aguarda a janela redimensionar


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

            // Procura o select da dispute category
            let select = document.querySelector('select[aria-label="Dispute category"]');

            // Se não encontrar, procura em Shadow DOMs
            if (!select) {
                const allElements = document.querySelectorAll('*');
                for (let el of allElements) {
                    if (el.shadowRoot) {
                        select = el.shadowRoot.querySelector('select[aria-label="Dispute category"]');
                        if (select) break;
                    }
                }
            }

            if (!select) {
                return {success: false, error: 'Select não encontrado'};
            }

            // Remove o disabled se necessário
            if (select.disabled) {
                select.disabled = false;
            }

            // Seleciona o valor
            select.value = category;
            select.dispatchEvent(new Event('change', { bubbles: true }));
            select.dispatchEvent(new Event('input', { bubbles: true }));

            return {success: true, value: select.value};
            """

            # Valores disponíveis:
            # "rateNotAsPerContractualAgreement" - Contractual rate not applied
            # "containerRolledByCarrier" - Container rolled by carrier
            # "agreedFreeTimeNotApplied" - Agreed free time not applied
            # "chargeIncurredDueToDelayByCarrier" - Charged due to delay by carrier
            # "others" - Others

            result = self.driver.execute_script(select_category_script, "rateNotAsPerContractualAgreement")

            logger.info("Preenchendo Expected Amount com valor padrão...")

            fill_expected_amount_script = """
            const billingItem = arguments[0];
            const amount = arguments[1];

            // 1. Busca diretamente pelo ID do mc-input
            const mcInputId = billingItem + '-expectedAmount';
            const mcInput = document.getElementById(mcInputId);

            if (!mcInput) {
                return {success: false, error: 'mc-input não encontrado com id: ' + mcInputId};
            }

            // 2. Remove disabled
            mcInput.removeAttribute('disabled');

            // 3. Acessa o Shadow DOM
            if (!mcInput.shadowRoot) {
                return {success: false, error: 'Shadow DOM não encontrado'};
            }

            // 4. Busca o input dentro do Shadow DOM
            const input = mcInput.shadowRoot.querySelector('input[type="text"]');

            if (!input) {
                return {success: false, error: 'Input interno não encontrado'};
            }

            // 5. Remove todos os bloqueios
            input.removeAttribute('disabled');
            input.removeAttribute('readonly');
            input.disabled = false;
            input.readOnly = false;

            // 6. Preenche o valor
            input.value = amount;

            // 7. Dispara eventos
            input.dispatchEvent(new Event('focus', { bubbles: true }));
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));
            input.dispatchEvent(new Event('blur', { bubbles: true }));

            // 8. Atualiza o input hidden também (por segurança)
            const hiddenInput = document.querySelector('input[type="number"][name="' + mcInputId + '"][style*="display:none"]');
            if (hiddenInput) {
                hiddenInput.value = amount;
            }

            return {success: true, value: input.value, hiddenValue: hiddenInput ? hiddenInput.value : 'not found'};
            """

            result = self.driver.execute_script(fill_expected_amount_script, "00000001", "1500.00")

            if not result.get('success'):
                logger.error(f"Erro ao preencher Expected Amount: {result.get('error')}")
                self.driver.save_screenshot("debug_erro_expected_amount.png")
                return {"success": False, "error": result.get('error')}

            logger.info("Preenchendo descrição da disputa...")

            fill_description_script = """
            const text = arguments[0];

            // Busca o textarea por name
            const textarea = document.querySelector('textarea[name="noteDescription"]');

            if (!textarea) {
                // Se não encontrar, procura em Shadow DOM
                const mcTextarea = document.querySelector('mc-textarea[name="noteDescription"]');
                if (mcTextarea && mcTextarea.shadowRoot) {
                    const shadowTextarea = mcTextarea.shadowRoot.querySelector('textarea');
                    if (shadowTextarea) {
                        shadowTextarea.value = text;
                        shadowTextarea.dispatchEvent(new Event('input', { bubbles: true }));
                        shadowTextarea.dispatchEvent(new Event('change', { bubbles: true }));
                        return {success: true, value: shadowTextarea.value};
                    }
                }
                return {success: false, error: 'Textarea não encontrado'};
            }

            // Preenche o textarea
            textarea.value = text;
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            textarea.dispatchEvent(new Event('change', { bubbles: true }));

            return {success: true, value: textarea.value};
            """

            result = self.driver.execute_script(fill_description_script, "TESTE")

            if not result.get('success'):
                logger.error(f"Erro ao preencher descrição: {result.get('error')}")
                self.driver.save_screenshot("debug_erro_description.png")
                return {"success": False, "error": result.get('error')}

            logger.info(f"✓ Descrição preenchida: {result.get('value')}")
            time.sleep(1)
            logger.info("Preenchendo informações de contato...")

            fill_contact_info_script = """
            const name = arguments[0];
            const email = arguments[1];
            const phone = arguments[2];

            function fillMcInput(mcInputId, value) {
                const mcInput = document.getElementById(mcInputId);
                if (!mcInput) {
                    return {success: false, error: 'mc-input não encontrado: ' + mcInputId};
                }

                // Preenche via Shadow DOM
                if (mcInput.shadowRoot) {
                    const input = mcInput.shadowRoot.querySelector('input[type="text"]');
                    if (input) {
                        input.value = value;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }

                // Preenche também o input hidden
                const hiddenInput = document.querySelector(`input[name="${mcInputId}"][style*="display:none"]`);
                if (hiddenInput) {
                    hiddenInput.value = value;
                }

                return {success: true};
            }

            // Preenche Name
            let result = fillMcInput('contactPerson', name);
            if (!result.success) return result;

            // Preenche Email
            result = fillMcInput('contactEmail', email);
            if (!result.success) return result;

            // Preenche Contact Number
            result = fillMcInput('contactTelNumber', phone);
            if (!result.success) return result;

            return {
                success: true, 
                name: name,
                email: email,
                phone: phone
            };
            """

            # Defina os valores aqui
            contact_name = "Fernando"
            contact_email = "fernando.conceicao@nitro.com.br"
            contact_phone = "+55 11 99999-9999"  # Coloque o telefone aqui

            result = self.driver.execute_script(
                fill_contact_info_script,
                contact_name,
                contact_email,
                contact_phone
            )

            if not result.get('success'):
                logger.error(f"Erro ao preencher informações de contato: {result.get('error')}")
                self.driver.save_screenshot("debug_erro_contact_info.png")
                return {"success": False, "error": result.get('error')}

            logger.info(f"✓ Informações de contato preenchidas:")
            logger.info(f"  - Name: {result.get('name')}")
            logger.info(f"  - Email: {result.get('email')}")
            logger.info(f"  - Phone: {result.get('phone')}")
            time.sleep(1)

            # Captura screenshot da página final
            self.driver.save_screenshot("debug_pagina_disputa.png")
            logger.info("Screenshot salvo: debug_pagina_disputa.png")

            logger.info("Página de disputa aberta com sucesso")

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