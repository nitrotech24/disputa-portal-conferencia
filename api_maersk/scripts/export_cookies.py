"""
Script SIMPLIFICADO para exportar cookies
Usa Chrome normal (sem automação)
"""
import json
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# Caminho onde salvar
COOKIES_FILE = Path(__file__).parent.parent / "artifacts" / "maersk_cookies.json"
COOKIES_FILE.parent.mkdir(exist_ok=True)


def export_cookies():
    print("=" * 80)
    print("EXPORTAÇÃO DE COOKIES - VERSÃO SIMPLES")
    print("=" * 80)
    print("\n📋 INSTRUÇÕES:")
    print("1. O Chrome vai abrir")
    print("2. FAÇA LOGIN MANUALMENTE no Maersk")
    print("3. Aguarde até ver a página logada (MyFinance, por exemplo)")
    print("4. Volte aqui e aperte ENTER")
    print("5. Os cookies serão salvos")
    print("\n" + "=" * 80)

    input("\nPressione ENTER para continuar...")

    # Chrome normal (sem flags anti-detecção)
    print("\n🌐 Abrindo Chrome...")
    options = Options()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)

    # Ir para Maersk
    print("🔗 Acessando Maersk.com...")
    driver.get("https://www.maersk.com")

    print("\n" + "=" * 80)
    print("✋ AGORA É COM VOCÊ!")
    print("=" * 80)
    print("\n👉 Faça LOGIN MANUALMENTE")
    print("👉 Depois de logar completamente, volte aqui e aperte ENTER\n")

    input("Pressione ENTER depois de fazer login...")

    # Salvar cookies
    print("\n💾 Salvando cookies...")
    cookies = driver.get_cookies()

    with open(COOKIES_FILE, 'w') as f:
        json.dump(cookies, f, indent=2)

    print(f"✅ Cookies salvos em: {COOKIES_FILE}")
    print(f"📊 Total: {len(cookies)} cookies")

    # Fechar
    print("\n🔄 Fechando em 3 segundos...")
    time.sleep(3)
    driver.quit()

    print("\n" + "=" * 80)
    print("✅ CONCLUÍDO!")
    print("=" * 80)
    print("\n💡 Agora rode o teste:")
    print("   python api_maersk\\tests\\test_create_dispute_web.py")
    print("=" * 80)


if __name__ == "__main__":
    export_cookies()