"""
auth.py
Fluxo de login na Hapag-Lloyd com Selenium (undetected-chromedriver).
Responsável por capturar e retornar o X-Token.
"""

import time
import logging
import os
from pathlib import Path

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from dotenv import load_dotenv
from api_hapag.storage import save_cookies, save_token

# --- CONFIG ---
START_URL = "https://www.hapag-lloyd.com/solutions/invoice-overview"

load_dotenv()
USERNAME = os.getenv("HL_USER")
PASSWORD = os.getenv("HL_PASS")

if not USERNAME or not PASSWORD:
    raise ValueError("Usuário e senha não configurados no .env (HL_USER / HL_PASS)")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def login_and_get_token() -> str | None:
    """
    Abre o navegador, faz login e retorna um novo X-Token.
    """
    logging.info("Iniciando Chrome para login...")
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")

    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    xtoken = None
    try:
        logging.info(f"Abrindo {START_URL}")
        driver.get(START_URL)

        # --- Fechar banner de cookies, se aparecer ---
        try:
            cookie_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Confirm My Choices')]"))
            )
            cookie_btn.click()
            logging.info("Banner de cookies fechado com sucesso")
        except TimeoutException:
            logging.info("Nenhum banner de cookies encontrado")

        # --- Login ---
        email = wait.until(EC.presence_of_element_located((By.ID, "signInName")))
        pwd = wait.until(EC.presence_of_element_located((By.ID, "password")))

        email.send_keys(USERNAME)
        pwd.send_keys(PASSWORD)

        btn = wait.until(EC.element_to_be_clickable((By.ID, "next")))
        driver.execute_script("arguments[0].click();", btn)
        logging.info("Cliquei em 'Log in'")

        # espera redirecionar e carregar a seção de disputas
        time.sleep(10)
        driver.get("https://www.hapag-lloyd.com/solutions/dispute-overview/#/?language=pt")
        time.sleep(5)

        # --- Captura token dos cookies (auth_prod) ---
        for cookie in driver.get_cookies():
            if cookie["name"] == "auth_prod":
                xtoken = cookie["value"]
                logging.info("XTOKEN capturado e salvo com sucesso")
                break

        # salva cookies e token
        save_cookies(driver.get_cookies())
        if xtoken:
            save_token(xtoken)

    except Exception as e:
        logging.error(f"Erro no login: {e}")

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    return xtoken
