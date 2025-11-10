import pyautogui
import time

print("🚀 Em 5 segundos, leve o mouse até o ponto que você quer clicar (ex: o botão 'Continue')...")
time.sleep(5)
x, y = pyautogui.position()
print(f"🧭 Coordenadas capturadas: X={x}, Y={y}")
