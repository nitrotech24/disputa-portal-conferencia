import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.token_service import TokenService
from services.auth_service import AuthService
from services.dispute_service import DisputeService
from utils.logger import setup_logger
import time

logger = setup_logger(__name__)


def check_all_invoice_types(invoice_number: str, customer_code: str):
    """
    Testa uma invoice em todos os tipos possíveis para ver onde ela aparece.
    """
    logger.info("=" * 80)
    logger.info(f"TESTANDO INVOICE {invoice_number} EM DIFERENTES STATUS")
    logger.info("=" * 80)

    token_service = TokenService()
    auth_service = AuthService(token_service)
    dispute_service = DisputeService(token_service, auth_service)

    # Lista de tipos conhecidos
    invoice_types = ["OPEN", "PAID", "OVERDUE", "DISPUTED", "CREDIT", "DEBIT"]

    results = {}

    for invoice_type in invoice_types:
        logger.info(f"\n[{invoice_type}] Buscando...")

        try:
            invoice_data = dispute_service.get_invoice_info(
                invoice_number=invoice_number,
                customer_code=customer_code,
                invoice_type=invoice_type
            )

            if invoice_data and invoice_data.get("invoices"):
                invoice = invoice_data["invoices"][0]
                results[invoice_type] = {
                    "encontrada": True,
                    "status": invoice.get("status"),
                    "valor": invoice.get("amount"),
                    "moeda": invoice.get("currency"),
                    "data": invoice.get("invoiceDate")
                }
                logger.info(f"✅ ENCONTRADA!")
                logger.info(f"   Status: {invoice.get('status')}")
                logger.info(f"   Valor: {invoice.get('currency')} {invoice.get('amount')}")
            else:
                results[invoice_type] = {"encontrada": False}
                logger.info(f"❌ Não encontrada")

            time.sleep(0.5)

        except Exception as e:
            results[invoice_type] = {"encontrada": False, "erro": str(e)}
            logger.error(f"❌ Erro: {e}")

    # Resumo
    logger.info("\n" + "=" * 80)
    logger.info("RESUMO")
    logger.info("=" * 80)

    encontradas = [t for t, r in results.items() if r.get("encontrada")]

    if encontradas:
        logger.info(f"\n✅ Invoice encontrada em: {', '.join(encontradas)}")
        for tipo in encontradas:
            r = results[tipo]
            logger.info(f"\n[{tipo}]")
            logger.info(f"  Status: {r.get('status')}")
            logger.info(f"  Valor: {r.get('moeda')} {r.get('valor')}")
    else:
        logger.warning("\n⚠️  Invoice não encontrada em nenhum tipo!")

    logger.info("=" * 80)

    return results


def discover_all_statuses_from_disputes(customer_code: str):
    """
    Busca todas as disputas e coleta os status únicos das invoices.
    """
    logger.info("=" * 80)
    logger.info("DESCOBRINDO TODOS OS STATUS POSSÍVEIS")
    logger.info("=" * 80)

    token_service = TokenService()
    auth_service = AuthService(token_service)
    dispute_service = DisputeService(token_service, auth_service)

    # Buscar todas as disputas
    logger.info("\n[1] Buscando todas as disputas...")
    all_disputes = dispute_service.list_all_disputes(customer_code)
    logger.info(f"✅ {len(all_disputes)} disputas encontradas")

    # Coletar invoices únicas
    invoice_numbers = list(set([d.get("invoiceNumber") for d in all_disputes if d.get("invoiceNumber")]))
    logger.info(f"✅ {len(invoice_numbers)} invoices únicas")

    # Testar algumas invoices em todos os tipos
    logger.info(f"\n[2] Testando primeiras 10 invoices em todos os tipos...")
    logger.info("=" * 80)

    all_statuses = set()
    type_counts = {}

    for idx, invoice_num in enumerate(invoice_numbers[:10], 1):
        logger.info(f"\n--- Invoice {idx}/10: {invoice_num} ---")

        for invoice_type in ["OPEN", "PAID", "OVERDUE", "DISPUTED"]:
            try:
                invoice_data = dispute_service.get_invoice_info(
                    invoice_number=invoice_num,
                    customer_code=customer_code,
                    invoice_type=invoice_type
                )

                if invoice_data and invoice_data.get("invoices"):
                    invoice = invoice_data["invoices"][0]
                    status = invoice.get("status", "Unknown")
                    all_statuses.add(status)

                    type_counts[invoice_type] = type_counts.get(invoice_type, 0) + 1

                    logger.info(f"✅ [{invoice_type}] Status: {status}")
                    break  # Encontrou, não precisa testar outros tipos

                time.sleep(0.3)

            except Exception as e:
                logger.error(f"❌ Erro em {invoice_type}: {e}")

    # Resultado final
    logger.info("\n" + "=" * 80)
    logger.info("DESCOBERTAS")
    logger.info("=" * 80)
    logger.info(f"\n📋 Status únicos encontrados: {', '.join(sorted(all_statuses))}")
    logger.info(f"\n📊 Distribuição por tipo:")
    for tipo, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {tipo}: {count} invoices")
    logger.info("=" * 80)

    return list(all_statuses)


def main():
    customer_code = "305S3073SPA"

    print("\n" + "=" * 80)
    print("ESCOLHA UMA OPÇÃO:")
    print("=" * 80)
    print("1 - Testar UMA invoice específica em todos os tipos")
    print("2 - Descobrir todos os status analisando disputas")
    print("=" * 80)

    opcao = input("\nOpção (1 ou 2): ").strip()

    if opcao == "1":
        invoice_num = input("Digite o número da invoice: ").strip()
        check_all_invoice_types(invoice_num, customer_code)

    elif opcao == "2":
        discover_all_statuses_from_disputes(customer_code)

    else:
        print("❌ Opção inválida!")


if __name__ == "__main__":
    main()