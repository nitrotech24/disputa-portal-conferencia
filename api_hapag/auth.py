"""
auth.py
Fluxo robusto de login na Hapag-Lloyd com Selenium (undetected-chromedriver).
Responsável por capturar o xtoken navegando até a aba de disputas.
"""

import os
import re
import time
import json
import logging
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementNotInteractableException
from dotenv import load_dotenv

from .storage import save_cookies, save_token, load_token

# --- CONFIG ---
START_URL = "https://www.hapag-lloyd.com/solutions/invoice-overview"
DISPUTE_URL = "https://www.hapag-lloyd.com/solutions/dispute-overview/#/?language=pt"

ARTIFACTS_DIR = Path("artifacts")
ARTIFACTS_DIR.mkdir(exist_ok=True)

load_dotenv()
USERNAME = os.getenv("HL_USER")
PASSWORD = os.getenv("HL_PASS")

if not USERNAME or not PASSWORD:
    raise ValueError("Usuário e senha não configurados no .env (HL_USER / HL_PASS)")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


# ---------- HELPERS ----------
def set_input_safe(driver, wait, xpath_list, value):
    """Preenche input de forma robusta (clicável, senão via JS)."""
    for xp in xpath_list:
        try:
            el = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
            try:
                el.click()
            except Exception:
                pass
            try:
                el.clear()
            except Exception:
                pass
            try:
                el.send_keys(value)
            except ElementNotInteractableException:
                driver.execute_script(
                    "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input'));",
                    el, value
                )
            return True
        except TimeoutException:
            try:
                el = driver.find_element(By.XPATH, xp)
                driver.execute_script(
                    "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input'));",
                    el, value
                )
                return True
            except Exception:
                continue
    return False


def extract_xtoken(driver) -> str | None:
    """Tenta extrair o token de várias fontes."""
    # 1. Cookies
    for cookie in driver.get_cookies():
        if cookie["name"] == "auth_prod":
            return cookie["value"]

    # 2. localStorage
    try:
        local_storage = driver.execute_script("return {...localStorage};")
        for k, v in local_storage.items():
            if "token" in k.lower() or "auth" in k.lower():
                return v
    except Exception:
        pass

    # 3. sessionStorage
    try:
        session_storage = driver.execute_script("return {...sessionStorage};")
        for k, v in session_storage.items():
            if "token" in k.lower() or "auth" in k.lower():
                return v
    except Exception:
        pass

    # 4. page_source
    try:
        page_source = driver.page_source
        token_patterns = [
            r'"x-token":\s*"([^"]+)"',
            r'"xtoken":\s*"([^"]+)"',
            r'"token":\s*"([^"]+)"'
        ]
        for pattern in token_patterns:
            matches = re.findall(pattern, page_source, re.IGNORECASE)
            if matches:
                return matches[0]
    except Exception:
        pass

    return None


# ---------- MAIN ----------
def get_xtoken(force_login: bool = False) -> str | None:
    """
    Retorna um token válido.
    - Se já existe salvo e force_login=False, retorna direto.
    - Se expirou ou force_login=True, faz login, navega até disputas e captura um novo.
    """
    if not force_login:
        token = load_token()
        if token:
            logging.info("Token já existente carregado de xtoken.txt")
            return token

    logging.info("Iniciando Chrome para login...")
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    xtoken = None
    try:
        logging.info(f"Abrindo {START_URL}")
        driver.get(START_URL)

        # Fecha banner de cookies
        try:
            cookie_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Confirm My Choices')]"))
            )
            cookie_btn.click()
            logging.info("Banner de cookies fechado")
        except TimeoutException:
            logging.info("Nenhum banner de cookies encontrado")

        # Login
        email_xps = ["//input[@id='signInName']", "//input[@type='email']"]
        pwd_xps = ["//input[@id='password']", "//input[@type='password']"]

        if not set_input_safe(driver, wait, email_xps, USERNAME):
            logging.error("Campo de e-mail não encontrado")
            return None
        if not set_input_safe(driver, wait, pwd_xps, PASSWORD):
            logging.error("Campo de senha não encontrado")
            return None

        try:
            btn = wait.until(EC.element_to_be_clickable((By.ID, "next")))
            driver.execute_script("arguments[0].click();", btn)
        except Exception:
            driver.execute_script("document.getElementById('next').click();")
        logging.info("Cliquei em 'Log in'")

        time.sleep(8)

        # Navegar até disputas
        logging.info(f"Navegando até {DISPUTE_URL}")
        driver.get(DISPUTE_URL)
        time.sleep(5)

        # Tenta capturar o xtoken
        xtoken = extract_xtoken(driver)

        if xtoken:
            save_token(xtoken)
            save_cookies(driver.get_cookies())
            logging.info("XTOKEN capturado e salvo com sucesso")
        else:
            logging.error("Não foi possível capturar XTOKEN")

    except Exception as e:
        logging.error(f"Erro no login: {e}")

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return xtoken
