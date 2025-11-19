"""
API Maersk - Sistema de Gestão de Disputas
Ponto de entrada principal da aplicação
"""
import sys
from pathlib import Path

# Adiciona o diretório pai ao path para imports funcionarem
sys.path.insert(0, str(Path(__file__).parent.parent))

from api_maersk.services.token_service import TokenService
from api_maersk.services.auth_service import AuthService
from api_maersk.services.dispute_service import DisputeService
from api_maersk.services.dispute_sync_service import DisputeSyncService
from api_maersk.services.dispute_sync_service_parallel import DisputeSyncServiceParallel
from api_maersk.repos.invoice_repository import InvoiceRepository
from api_maersk.repos.disputa_repository import DisputaRepository
from api_maersk.config.settings import CUSTOMER_CODE_MAPPING, DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from api_maersk.utils.logger import setup_logger
import time
import mysql.connector
from api_maersk.scripts.import_missing_invoices import get_missing_invoices_from_disputes, \
    fetch_and_insert_missing_invoices

logger = setup_logger(__name__)


def _conn():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def get_disputas_desatualizadas(customer_code: str):
    """
    Busca disputas que precisam ser atualizadas:
    - updated_at > 2 horas
    - Status NÃO final (para pegar mudanças de status)
    """
    sql = """
    SELECT 
        d.dispute_number,
        d.status,
        i.customer_code,
        d.updated_at
    FROM disputa d
    JOIN invoice i ON d.invoice_id = i.id
    WHERE i.armador = 'MAERSK'
      AND i.customer_code = %s
      AND d.updated_at < NOW() - INTERVAL 2 HOUR
      AND d.status NOT IN ('Accepted - Invoice cancellation and rebill', 'REJECTED', 'CLOSED', 'CANCELLED')
    """

    with _conn() as conn:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, (customer_code,))
        return cur.fetchall()


def atualizar_disputas_desatualizadas(customer_code: str, sync_service: DisputeSyncService):
    """
    Atualiza disputas desatualizadas buscando dados completos da API.
    """
    logger.info(f"[3/3] Verificando disputas desatualizadas para {customer_code}...")

    disputas = get_disputas_desatualizadas(customer_code)

    if not disputas:
        logger.info("Nenhuma disputa precisa ser atualizada")
        return 0

    logger.info(f"Encontradas {len(disputas)} disputas para atualizar")

    atualizadas = 0
    erros = 0

    for idx, disputa in enumerate(disputas, 1):
        dispute_id = str(disputa['dispute_number'])
        status_atual = disputa['status']

        try:
            logger.info(f"  [{idx}/{len(disputas)}] Atualizando disputa {dispute_id} (status: {status_atual})...")

            result = sync_service.update_dispute_status(dispute_id, customer_code)

            if result.get('success'):
                atualizadas += 1
                logger.info(f"    Atualizada: {result.get('status')}")
            else:
                erros += 1
                logger.warning(f"    Erro: {result.get('error')}")

            # Rate limit
            time.sleep(0.5)

        except Exception as e:
            erros += 1
            logger.error(f"    Erro ao atualizar {dispute_id}: {e}")

    logger.info(f"Resultado: {atualizadas} atualizadas, {erros} erros")
    return atualizadas


def importar_invoices_faltantes(customer_code: str, dispute_service: DisputeService, invoice_repo: InvoiceRepository):
    """
    Identifica e importa invoices que têm disputa mas não estão no banco.
    """
    logger.info(f"[1/3] Verificando invoices faltantes para {customer_code}...")
    missing_invoices = get_missing_invoices_from_disputes(customer_code)

    if missing_invoices:
        logger.info(f"Encontradas {len(missing_invoices)} invoices faltantes")
        stats = fetch_and_insert_missing_invoices(customer_code, missing_invoices)
        return stats.get('inseridas_banco', 0)
    else:
        logger.info("Nenhuma invoice faltante")
        return 0


def main():
    print("=" * 80)
    print("EXECUÇÃO AUTOMÁTICA COMPLETA - API MAERSK")
    print("=" * 80)
    print("\nEste processo irá:")
    print("1. Importar invoices com disputa que não estão no banco")
    print("2. Sincronizar todas as disputas")
    print("3. Atualizar disputas desatualizadas (>2h, status não final)")
    print("=" * 80)

    # Inicializar serviços
    logger.info("Inicializando serviços...")
    token_service = TokenService()
    auth_service = AuthService(token_service)
    dispute_service = DisputeService(token_service, auth_service)
    invoice_repo = InvoiceRepository()
    disputa_repo = DisputaRepository()

    # Serviço paralelo para sync inicial
    sync_service_parallel = DisputeSyncServiceParallel(
        dispute_service,
        invoice_repo,
        disputa_repo,
        max_workers=3
    )

    # Serviço normal para updates individuais
    sync_service = DisputeSyncService(
        dispute_service,
        invoice_repo,
        disputa_repo
    )

    # Processar todos os clientes
    clientes = list(CUSTOMER_CODE_MAPPING.keys())
    total_disputas_sincronizadas = 0
    total_disputas_atualizadas = 0
    total_invoices_importadas = 0

    start_time = time.time()

    for idx, customer_code in enumerate(clientes, 1):
        print(f"\n{'=' * 80}")
        print(f"CLIENTE {idx}/{len(clientes)}: {customer_code}")
        print(f"{'=' * 80}")

        try:
            # Passo 1: Importar invoices faltantes
            invoices_importadas = importar_invoices_faltantes(customer_code, dispute_service, invoice_repo)
            total_invoices_importadas += invoices_importadas

            if invoices_importadas > 0:
                logger.info(f"{invoices_importadas} invoices importadas")

            # Passo 2: Sincronizar disputas
            logger.info(f"[2/3] Sincronizando disputas...")
            stats = sync_service_parallel.sync_disputes_parallel(customer_code, limit=10000)

            if "erro" not in stats:
                total_disputas_sincronizadas += stats.get('disputas_salvas', 0)

            # Passo 3: Atualizar disputas desatualizadas
            disputas_atualizadas = atualizar_disputas_desatualizadas(customer_code, sync_service)
            total_disputas_atualizadas += disputas_atualizadas

            # Resumo do cliente
            print(f"\nResultado:")
            print(f"  Invoices importadas: {invoices_importadas}")
            print(f"  Total invoices: {stats.get('total_invoices', 0)}")
            print(f"  Disputas sincronizadas: {stats.get('disputas_salvas', 0)}")
            print(f"  Disputas atualizadas: {disputas_atualizadas}")

            # Pausa entre clientes
            if idx < len(clientes):
                logger.info(f"\nPausa de 5s antes do proximo cliente...\n")
                time.sleep(5)

        except Exception as e:
            logger.error(f"Erro ao processar {customer_code}: {e}")
            continue

    elapsed = time.time() - start_time

    # Resumo final
    print(f"\n{'=' * 80}")
    print("EXECUÇÃO CONCLUÍDA")
    print(f"{'=' * 80}")
    print(f"Total de clientes processados: {len(clientes)}")
    print(f"Total de invoices importadas: {total_invoices_importadas}")
    print(f"Total de disputas sincronizadas: {total_disputas_sincronizadas}")
    print(f"Total de disputas atualizadas: {total_disputas_atualizadas}")
    print(f"Tempo total: {elapsed:.1f} segundos")
    print(f"{'=' * 80}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nPrograma interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        sys.exit(1)