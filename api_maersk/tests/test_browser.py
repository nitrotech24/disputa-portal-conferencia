"""
Teste simples para validar se o ChromeDriver está funcionando corretamente.
Abre o site da Maersk, aguarda alguns segundos e fecha.
"""

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

def main():
    print("=" * 80)
    print("🔧 TESTE: ABERTURA DO CHROME VIA SELENIUM")
    print("=" * 80)

    try:
        # Configurações do Chrome
        chrome_options = Options()
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Inicializa o driver
        print("🚀 Iniciando ChromeDriver...")
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager(driver_version=None).install()),
            options=chrome_options
        )

        # Acessa o site da Maersk
        print("🌐 Acessando https://www.maersk.com ...")
        driver.get("https://www.maersk.com/")
        time.sleep(10)  # Mantém aberto 10 segundos pra você ver

        print("✅ Sucesso! Chrome abriu e navegou normalmente.")
    except WebDriverException as e:
        print("❌ Erro ao abrir o ChromeDriver:")
        print(str(e))
    except Exception as e:
        print("❌ Erro inesperado:")
        print(str(e))
    finally:
        try:
            driver.quit()
            print("🧹 Chrome encerrado.")
        except:
            pass

    print("=" * 80)
    print("🏁 TESTE FINALIZADO")
    print("=" * 80)


if __name__ == "__main__":
    main()
