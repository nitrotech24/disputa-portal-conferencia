from api_hapag.services.consulta_status import atualizar_status_disputa

if __name__ == "__main__":
    # Exemplo: disputa_id=2 (no seu banco), dispute_number=3893800 (Hapag)
    atualizar_status_disputa(disputa_id=2, dispute_number=3893800)
