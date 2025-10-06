import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from api_maersk.services.token_service import TokenService
from api_maersk.services.auth_service import AuthService
from api_maersk.services.dispute_service import DisputeService
from api_maersk.repos.invoice_repository import InvoiceRepository
from api_maersk.utils.logger import setup_logger
import mysql.connector
from api_maersk.config.settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
import time

from datetime import datetime
import re

logger = setup_logger(__name__)


def convert_microsoft_date(date_string: str) -> str:
    """
    Converte data do formato Microsoft JSON '/Date(1757548800000)/'
    para formato MySQL 'YYYY-MM-DD HH:MM:SS'
    """
    if not date_string:
        return None

    try:
        # Extrair o timestamp em milissegundos
        match = re.search(r'/Date\((\d+)\)/', str(date_string))
        if match:
            timestamp_ms = int(match.group(1))
            timestamp_s = timestamp_ms / 1000
            dt = datetime.fromtimestamp(timestamp_s)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        else:
            # Se já está em formato normal, retorna como está
            return date_string
    except Exception as e:
        logger.warning(f"Erro ao converter data {date_string}: {e}")
        return None


def _conn():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def insert_invoice_into_db(invoice_data: dict) -> bool:
    """
    Insere uma invoice no banco de dados.

    Args:
        invoice_data: Dict com dados da invoice

    Returns:
        True se inseriu com sucesso, False caso contrário
    """
    try:
        sql = """
        INSERT INTO invoice (numero_invoice, armador, customer_code, customer_name, data_emissao_invoice, valor, moeda, status, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(3))
        ON DUPLICATE KEY UPDATE
            data_emissao_invoice = VALUES(data_emissao_invoice),
            valor = VALUES(valor),
            moeda = VALUES(moeda),
            status = VALUES(status),
            customer_code = VALUES(customer_code),
            customer_name = VALUES(customer_name),
            updated_at = NOW(3)
        """

        with _conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (
                invoice_data.get("numero_invoice"),
                invoice_data.get("armador", "MAERSK"),
                invoice_data.get("customer_code"),
                invoice_data.get("customer_name"),
                invoice_data.get("data_emissao_invoice"),
                invoice_data.get("valor"),
                invoice_data.get("moeda"),
                invoice_data.get("status")
            ))
            conn.commit()
            logger.info(
                f"✅ Invoice {invoice_data['numero_invoice']} inserida no banco ({invoice_data['customer_code']})")
            return True

    except Exception as e:
        logger.error(f"❌ Erro ao inserir invoice {invoice_data.get('numero_invoice')}: {e}")
        return False


def fetch_and_insert_missing_invoices(customer_code: str, invoice_numbers: list) -> dict:
    """
    Busca invoices na API e insere no banco de dados.

    Args:
        customer_code: Código do customer (ex: "305S3073SPA")
        invoice_numbers: Lista de números de invoices para buscar

    Returns:
        Dict com estatísticas do processo
    """
    logger.info("=" * 80)
    logger.info("BUSCANDO E INSERINDO INVOICES NO BANCO")
    logger.info("=" * 80)

    # Inicializar serviços
    token_service = TokenService()
    auth_service = AuthService(token_service)
    dispute_service = DisputeService(token_service, auth_service)

    # Estatísticas
    stats = {
        "total_solicitadas": len(invoice_numbers),
        "encontradas_api": 0,
        "nao_encontradas_api": 0,
        "inseridas_banco": 0,
        "erros_insercao": 0,
        "erros_busca": 0
    }

    logger.info(f"\n📋 Total de invoices para processar: {len(invoice_numbers)}")
    logger.info("=" * 80)

    # Processar cada invoice
    for idx, invoice_num in enumerate(invoice_numbers, 1):
        try:
            logger.info(f"\n[{idx}/{len(invoice_numbers)}] Processando invoice {invoice_num}...")

            # 1. Buscar invoice na API - TESTA TODOS OS STATUS POSSÍVEIS
            invoice_types_to_try = ["PAID", "OPEN", "OVERDUE", "DISPUTED", "CREDIT", "DEBIT"]
            invoice_data = None

            for invoice_type in invoice_types_to_try:
                invoice_data = dispute_service.get_invoice_info(
                    invoice_number=invoice_num,
                    customer_code=customer_code,
                    invoice_type=invoice_type
                )

                if invoice_data and invoice_data.get("invoices"):
                    logger.info(f"   Encontrada em: {invoice_type}")
                    break

            # 2. Verificar se encontrou
            if invoice_data and invoice_data.get("invoices"):
                invoice = invoice_data["invoices"][0]
                stats["encontradas_api"] += 1

                # DEBUG: Ver todos os campos disponíveis
                logger.info(f"   Campos disponíveis: {list(invoice.keys())[:20]}")

                # Converter data
                raw_date = invoice.get("invoiceDate")
                converted_date = convert_microsoft_date(raw_date)

                logger.info(f"   Data original: {raw_date}")
                logger.info(f"   Data convertida: {converted_date}")

                # Preparar dados para inserção
                invoice_to_insert = {
                    "numero_invoice": invoice.get("invoiceNo") or invoice.get("invoiceNumber"),
                    "armador": "MAERSK",
                    "customer_code": customer_code,
                    "customer_name": invoice.get("priceOwnerName"),
                    "data_emissao_invoice": converted_date,
                    "valor": invoice.get("invoicedAmount") or invoice.get("openAmount"),
                    "moeda": invoice.get("currency"),
                    "status": invoice.get("invoiceStatus") or invoice.get("status", "PAID")
                }

                logger.info(f"   API ✅ - Valor: {invoice_to_insert['moeda']} {invoice_to_insert['valor']}")

                # 3. Inserir no banco
                if insert_invoice_into_db(invoice_to_insert):
                    stats["inseridas_banco"] += 1
                    logger.info(f"   BD ✅ - Invoice inserida com sucesso!")
                else:
                    stats["erros_insercao"] += 1
                    logger.warning(f"   BD ⚠️  - Erro ao inserir no banco")

            else:
                stats["nao_encontradas_api"] += 1
                logger.warning(f"   API ⚠️  - Invoice não encontrada")

            # Delay para não sobrecarregar API
            if idx % 10 == 0:
                logger.info(f"\n⏸️  Pausa de 2s (processadas {idx}/{len(invoice_numbers)})...")
                time.sleep(2)
            else:
                time.sleep(0.5)

        except Exception as e:
            stats["erros_busca"] += 1
            logger.error(f"❌ Erro ao processar invoice {invoice_num}: {e}")
            continue

    # Relatório final
    logger.info("\n" + "=" * 80)
    logger.info("RELATÓRIO FINAL")
    logger.info("=" * 80)
    logger.info(f"📊 Total processadas: {stats['total_solicitadas']}")
    logger.info(f"🔍 Encontradas na API: {stats['encontradas_api']}")
    logger.info(f"💾 Inseridas no banco: {stats['inseridas_banco']}")
    logger.info(f"⚠️  Não encontradas na API: {stats['nao_encontradas_api']}")
    logger.info(f"❌ Erros de inserção: {stats['erros_insercao']}")
    logger.info(f"❌ Erros de busca: {stats['erros_busca']}")
    logger.info("=" * 80)

    return stats


def get_missing_invoices_from_disputes(customer_code: str) -> list:
    """
    Identifica invoices que têm disputa mas não estão no banco.
    Retorna lista de números de invoices para buscar.
    """
    logger.info("=" * 80)
    logger.info("IDENTIFICANDO INVOICES FALTANTES")
    logger.info("=" * 80)

    token_service = TokenService()
    auth_service = AuthService(token_service)
    dispute_service = DisputeService(token_service, auth_service)
    invoice_repo = InvoiceRepository()

    # 1. Buscar todas as disputas da API
    logger.info("\n[1] Buscando disputas da API...")
    all_disputes = dispute_service.list_all_disputes(customer_code)
    logger.info(f"✅ {len(all_disputes)} disputas encontradas na API")

    # 2. Buscar todas as invoices do banco
    logger.info("\n[2] Buscando invoices do banco...")
    all_invoices = invoice_repo.fetch_invoices_maersk(limit=100000)
    invoice_numbers_in_db = {inv["numero_invoice"] for inv in all_invoices}
    logger.info(f"✅ {len(invoice_numbers_in_db)} invoices MAERSK no banco")

    # 3. Identificar invoices faltantes
    logger.info("\n[3] Identificando invoices faltantes...")
    missing_invoices = []
    for dispute in all_disputes:
        invoice_num = dispute.get("invoiceNumber")
        if invoice_num and invoice_num not in invoice_numbers_in_db:
            missing_invoices.append(invoice_num)

    # Remover duplicatas
    missing_invoices = list(set(missing_invoices))

    logger.info(f"⚠️  {len(missing_invoices)} invoices faltantes identificadas")
    logger.info("=" * 80)

    return missing_invoices


def main():
    """
    Fluxo completo:
    1. Identifica invoices que têm disputa mas não estão no BD
    2. Busca essas invoices na API
    3. Insere no banco de dados
    """
    customer_code = "305S3073SPA"

    logger.info("\n" + "=" * 80)
    logger.info("IMPORTAÇÃO DE INVOICES COM DISPUTA")
    logger.info("=" * 80)
    logger.info("\n📋 Este script vai:")
    logger.info("1. Identificar invoices com disputa que não estão no banco")
    logger.info("2. Buscar essas invoices na API da Maersk")
    logger.info("3. Inserir automaticamente no banco de dados")
    logger.info("\n" + "=" * 80)

    # Passo 1: Identificar invoices faltantes
    missing_invoices = get_missing_invoices_from_disputes(customer_code)

    if not missing_invoices:
        logger.info("\n✅ Nenhuma invoice faltante! Todas as disputas têm invoice no banco.")
        return

    # Confirmação
    logger.info(f"\n⚠️  Serão processadas {len(missing_invoices)} invoices")
    logger.info(f"⏱️  Tempo estimado: ~{int(len(missing_invoices) * 0.7 / 60)} minutos")
    logger.info("\nIniciando em 3 segundos... (Ctrl+C para cancelar)")
    time.sleep(3)

    # Passo 2: Buscar e inserir
    stats = fetch_and_insert_missing_invoices(customer_code, missing_invoices)

    # Resultado final
    logger.info("\n" + "=" * 80)
    logger.info("PROCESSO CONCLUÍDO!")
    logger.info("=" * 80)

    if stats["inseridas_banco"] > 0:
        logger.info(f"\n✅ {stats['inseridas_banco']} invoices importadas com sucesso!")
        logger.info("\n💡 Próximo passo: Execute 'py tests/sync_all_disputes_full.py'")
        logger.info("   para sincronizar as disputas dessas novas invoices")
    else:
        logger.warning("\n⚠️  Nenhuma invoice foi inserida no banco")

    logger.info("=" * 80)


if __name__ == "__main__":
    main()