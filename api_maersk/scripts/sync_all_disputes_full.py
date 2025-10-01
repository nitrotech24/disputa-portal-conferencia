import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from services.token_service import TokenService
from services.auth_service import AuthService
from services.dispute_service import DisputeService
from services.dispute_sync_service import DisputeSyncService
from repos.invoice_repository import InvoiceRepository
from repos.disputa_repository import DisputaRepository
from utils.logger import setup_logger

logger = setup_logger(__name__)


def sync_all_disputes_comprehensive(customer_code: str):
    """
    Sincronização COMPLETA de disputas:
    1. Lista TODAS as disputas da API
    2. Para cada disputa, verifica se a invoice existe no banco
    3. Se existir, salva a disputa
    4. Se NÃO existir, registra para análise posterior
    """
    logger.info("=" * 80)
    logger.info("SINCRONIZAÇÃO COMPLETA DE DISPUTAS")
    logger.info("=" * 80)

    # Inicializar serviços
    token_service = TokenService()
    auth_service = AuthService(token_service)
    dispute_service = DisputeService(token_service, auth_service)
    invoice_repo = InvoiceRepository()
    disputa_repo = DisputaRepository()

    # 1. Buscar TODAS as disputas da API
    logger.info(f"\n[1] Buscando todas as disputas para {customer_code}...")
    all_disputes = dispute_service.list_all_disputes(customer_code)

    if not all_disputes:
        logger.warning("❌ Nenhuma disputa encontrada na API")
        return

    logger.info(f"✅ Encontradas {len(all_disputes)} disputas na API")

    # 2. Buscar TODAS as invoices MAERSK do banco (sem limite)
    logger.info("\n[2] Buscando todas as invoices MAERSK do banco...")
    all_invoices = invoice_repo.fetch_invoices_maersk(limit=100000)  # limite alto para pegar todas
    logger.info(f"✅ Encontradas {len(all_invoices)} invoices no banco")

    # 3. Criar mapa: invoice_number -> invoice_id para lookup rápido
    invoice_map = {inv["numero_invoice"]: inv["id"] for inv in all_invoices}

    # 4. Estatísticas
    stats = {
        "total_disputas_api": len(all_disputes),
        "total_invoices_bd": len(all_invoices),
        "disputas_salvas": 0,
        "disputas_sem_invoice": 0,
        "invoices_nao_encontradas": []
    }

    # 5. Processar cada disputa
    logger.info("\n[3] Processando disputas...")
    logger.info("=" * 80)

    for idx, dispute in enumerate(all_disputes, 1):
        invoice_num = dispute.get("invoiceNumber")
        dispute_id = dispute.get("ohpDisputeId")
        status = dispute.get("statusDescription", "Unknown")

        if not invoice_num or not dispute_id:
            logger.warning(f"⚠️  Disputa {idx} sem invoice ou ID, pulando...")
            continue

        # Verificar se a invoice existe no banco
        if invoice_num in invoice_map:
            invoice_id = invoice_map[invoice_num]

            # Salvar disputa no banco
            disputa_repo.insert_or_update(
                invoice_id=invoice_id,
                dispute_number=int(dispute_id),
                status=status
            )

            stats["disputas_salvas"] += 1

            if idx % 10 == 0:  # Log a cada 10 disputas
                logger.info(f"Progresso: {idx}/{len(all_disputes)} disputas processadas...")
        else:
            # Invoice NÃO está no banco
            stats["disputas_sem_invoice"] += 1
            stats["invoices_nao_encontradas"].append(invoice_num)

    # 6. Relatório final
    logger.info("\n" + "=" * 80)
    logger.info("RELATÓRIO FINAL")
    logger.info("=" * 80)
    logger.info(f"📊 Total de disputas na API: {stats['total_disputas_api']}")
    logger.info(f"📦 Total de invoices no banco: {stats['total_invoices_bd']}")
    logger.info(f"✅ Disputas salvas com sucesso: {stats['disputas_salvas']}")
    logger.info(f"⚠️  Disputas SEM invoice no banco: {stats['disputas_sem_invoice']}")

    if stats['disputas_sem_invoice'] > 0:
        logger.info(f"\n📋 Primeiras 20 invoices NÃO encontradas no banco:")
        for inv_num in stats['invoices_nao_encontradas'][:20]:
            logger.info(f"   - {inv_num}")

        if len(stats['invoices_nao_encontradas']) > 20:
            logger.info(f"   ... e mais {len(stats['invoices_nao_encontradas']) - 20} invoices")

    logger.info("=" * 80)

    # Taxa de cobertura
    if stats['total_disputas_api'] > 0:
        cobertura = (stats['disputas_salvas'] / stats['total_disputas_api']) * 100
        logger.info(f"📈 Taxa de cobertura: {cobertura:.1f}%")

    logger.info("=" * 80)

    return stats


def main():
    customer_code = "305S3073SPA"

    logger.info("\n⚠️  Este script vai:")
    logger.info("1. Listar TODAS as disputas da API")
    logger.info("2. Salvar apenas as disputas de invoices que existem no banco")
    logger.info("3. Mostrar quais invoices com disputa NÃO estão no banco\n")

    stats = sync_all_disputes_comprehensive(customer_code)

    if stats:
        logger.info("\n✅ Sincronização completa finalizada!")


if __name__ == "__main__":
    main()