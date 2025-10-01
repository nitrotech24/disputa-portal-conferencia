import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.token_service import TokenService
from services.auth_service import AuthService
from services.dispute_service import DisputeService
from utils.logger import setup_logger
import json

logger = setup_logger(__name__)


def inspect_all_dispute_fields(customer_code: str):
    """
    Busca disputas e mostra TODOS os campos disponíveis na API.
    """
    logger.info("=" * 80)
    logger.info("INSPECIONANDO CAMPOS DAS DISPUTAS")
    logger.info("=" * 80)

    token_service = TokenService()
    auth_service = AuthService(token_service)
    dispute_service = DisputeService(token_service, auth_service)

    # Buscar todas as disputas
    logger.info("\nBuscando disputas da API...")
    all_disputes = dispute_service.list_all_disputes(customer_code)

    if not all_disputes:
        logger.error("Nenhuma disputa encontrada!")
        return

    logger.info(f"✅ {len(all_disputes)} disputas encontradas")

    # Pegar a primeira disputa como exemplo
    first_dispute = all_disputes[0]

    logger.info("\n" + "=" * 80)
    logger.info("CAMPOS DA PRIMEIRA DISPUTA:")
    logger.info("=" * 80)

    # Listar todos os campos
    logger.info("\nLista de campos disponíveis:")
    for idx, key in enumerate(first_dispute.keys(), 1):
        value = first_dispute[key]
        value_type = type(value).__name__

        # Truncar valores muito longos
        if isinstance(value, str) and len(str(value)) > 50:
            value_display = str(value)[:50] + "..."
        else:
            value_display = value

        logger.info(f"{idx:3}. {key:30} = {value_display} ({value_type})")

    # Mostrar JSON completo da primeira disputa
    logger.info("\n" + "=" * 80)
    logger.info("JSON COMPLETO DA PRIMEIRA DISPUTA:")
    logger.info("=" * 80)
    print(json.dumps(first_dispute, indent=2, ensure_ascii=False))

    # Analisar campos de todas as disputas para ver valores únicos
    logger.info("\n" + "=" * 80)
    logger.info("ANÁLISE DE VALORES ÚNICOS:")
    logger.info("=" * 80)

    # Coletar valores únicos para campos importantes
    important_fields = [
        'statusDescription',
        'statusCode',
        'reasonCode',
        'reasonDescription',
        'currency'
    ]

    for field in important_fields:
        unique_values = set()
        for dispute in all_disputes:
            value = dispute.get(field)
            if value:
                unique_values.add(str(value))

        logger.info(f"\n{field}:")
        for value in sorted(unique_values):
            logger.info(f"  - {value}")

    # Estatísticas
    logger.info("\n" + "=" * 80)
    logger.info("ESTATÍSTICAS:")
    logger.info("=" * 80)
    logger.info(f"Total de disputas analisadas: {len(all_disputes)}")
    logger.info(f"Total de campos por disputa: {len(first_dispute.keys())}")

    # Campos nulos
    logger.info("\nCampos que frequentemente são nulos:")
    for key in first_dispute.keys():
        null_count = sum(1 for d in all_disputes if d.get(key) is None)
        if null_count > len(all_disputes) * 0.1:  # Mais de 10% nulos
            percentage = (null_count / len(all_disputes)) * 100
            logger.info(f"  {key}: {percentage:.1f}% nulos ({null_count}/{len(all_disputes)})")

    logger.info("=" * 80)


def main():
    customer_code = "305S3073SPA"

    logger.info("\nEste script vai:")
    logger.info("1. Buscar todas as disputas da API")
    logger.info("2. Mostrar TODOS os campos disponíveis")
    logger.info("3. Mostrar valores únicos dos campos importantes")
    logger.info("4. Ajudar a decidir quais campos salvar no banco\n")

    inspect_all_dispute_fields(customer_code)


if __name__ == "__main__":
    main()