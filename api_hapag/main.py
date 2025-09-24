"""
main.py
Ponto de entrada para consultas.
"""

import sys
import json
import logging
from .consulta import consultar_disputa

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def main():
    if len(sys.argv) < 2:
        print("Uso: python -m api_hapag.main <dispute_id>")
        return

    try:
        dispute_id = int(sys.argv[1])
    except ValueError:
        logging.error("O ID da disputa deve ser numérico")
        return

    result = consultar_disputa(dispute_id)
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        logging.error("Consulta falhou")


if __name__ == "__main__":
    main()
