from api_hapag.services.dispute_service import enviar_disputa_hapag
from api_hapag.services.token_service import get_valid_token

# Valida token
token = get_valid_token()
if not token:
    print("❌ Token inválido")
    exit()

# Envia disputa
resultado = enviar_disputa_hapag(
    invoice_id=123,                    # ← ALTERE: ID do banco
    invoice_number="2014948646",       # ← ALTERE: Número da invoice
    shipment_number="35861037",        # ← ALTERE: BL/Booking
    disputed_amount="2560",            # ← ALTERE: Valor
    contact_email="seu@email.com",     # ← ALTERE: Email
    dispute_text="Problema..."         # ← ALTERE: Descrição
)

if resultado:
    print(f"✅ Disputa {resultado['disputeNumber']} criada!")
else:
    print("❌ Erro ao criar disputa")