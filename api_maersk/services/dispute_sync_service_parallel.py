from services.dispute_service import DisputeService
from repos.invoice_repository import InvoiceRepository
from repos.disputa_repository import DisputaRepository
from utils.logger import setup_logger
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

logger = setup_logger(__name__)


class DisputeSyncServiceParallel:
    def __init__(
            self,
            dispute_service: DisputeService,
            invoice_repo: InvoiceRepository,
            disputa_repo: DisputaRepository,
            max_workers: int = 10  # 🚀 Número de threads simultâneas
    ):
        self.dispute_service = dispute_service
        self.invoice_repo = invoice_repo
        self.disputa_repo = disputa_repo
        self.max_workers = max_workers

    def _process_single_invoice(self, invoice: dict, dispute_map: dict, customer_code: str) -> dict:
        """
        Processa uma única invoice (será executada em paralelo).
        """
        invoice_id = invoice["id"]
        numero_invoice = invoice["numero_invoice"]

        result = {
            "invoice_id": invoice_id,
            "numero_invoice": numero_invoice,
            "has_dispute": False,
            "success": False,
            "error": None
        }

        try:
            if numero_invoice in dispute_map:
                dispute = dispute_map[numero_invoice]
                dispute_id = dispute.get("ohpDisputeId")
                status = dispute.get("statusDescription", "Unknown")

                logger.info(f"✅ Invoice {numero_invoice} tem disputa {dispute_id} (Cliente: {customer_code})")

                self.disputa_repo.insert_or_update(
                    invoice_id=invoice_id,
                    dispute_number=int(dispute_id),
                    status=status,
                    customer_code=customer_code  # ✅ ADICIONAR ESTA LINHA
                )

                result["has_dispute"] = True
                result["success"] = True
                result["dispute_id"] = dispute_id
                result["status"] = status
            else:
                logger.info(f"ℹ️  Invoice {numero_invoice} sem disputa no cliente {customer_code}")
                result["success"] = True

        except Exception as e:
            logger.error(f"❌ Erro ao processar invoice {numero_invoice}: {e}")
            result["error"] = str(e)

        return result

    def sync_disputes_parallel(self, customer_code: str, limit: int = 20):
        """
        Sincroniza disputas EM PARALELO.
        Muito mais rápido! 🚀
        """
        logger.info(f"🚀 Iniciando sincronização PARALELA de disputas para {customer_code}")
        logger.info(f"⚙️  Usando {self.max_workers} threads simultâneas")

        # 1. Buscar TODAS as disputas da API
        logger.info("📡 Buscando todas as disputas da API...")
        all_disputes = self.dispute_service.list_all_disputes(customer_code)

        if not all_disputes:
            logger.warning("⚠️  Nenhuma disputa encontrada na API")
            return {"erro": "Nenhuma disputa na API"}

        logger.info(f"✅ Encontradas {len(all_disputes)} disputas na API")

        # 2. Criar mapa: invoiceNumber -> dispute
        dispute_map = {}
        for dispute in all_disputes:
            invoice_num = dispute.get("invoiceNumber")
            if invoice_num:
                dispute_map[invoice_num] = dispute

        logger.info(f"🗺️  Mapa criado com {len(dispute_map)} invoices únicas")

        # 3. Buscar invoices MAERSK do banco
        invoices = self.invoice_repo.fetch_invoices_maersk(limit=limit)
        logger.info(f"🗄️  Encontradas {len(invoices)} invoices no banco")

        if not invoices:
            logger.warning("⚠️  Nenhuma invoice encontrada no banco")
            return {"erro": "Nenhuma invoice no banco"}

        stats = {
            "total_invoices": len(invoices),
            "com_disputa": 0,
            "sem_disputa": 0,
            "disputas_salvas": 0,
            "erros": 0
        }

        # 4. 🚀 PROCESSAR EM PARALELO
        logger.info(f"🚀 Processando {len(invoices)} invoices em paralelo...")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submeter todas as tarefas
            futures = {
                executor.submit(
                    self._process_single_invoice,
                    invoice,
                    dispute_map,
                    customer_code
                ): invoice for invoice in invoices
            }

            # Processar resultados conforme completam
            for future in as_completed(futures):
                result = future.result()

                if result["success"]:
                    if result["has_dispute"]:
                        stats["com_disputa"] += 1
                        stats["disputas_salvas"] += 1
                    else:
                        stats["sem_disputa"] += 1
                else:
                    stats["erros"] += 1
                    logger.error(f"❌ Erro: {result['error']}")

        # Retornar status
        logger.info("=" * 80)
        logger.info("✅ SINCRONIZAÇÃO PARALELA CONCLUÍDA")
        logger.info("=" * 80)
        logger.info(f"📊 Total de invoices: {stats['total_invoices']}")
        logger.info(f"✅ Com disputa: {stats['com_disputa']}")
        logger.info(f"ℹ️  Sem disputa: {stats['sem_disputa']}")
        logger.info(f"💾 Disputas salvas: {stats['disputas_salvas']}")
        logger.info(f"❌ Erros: {stats['erros']}")
        logger.info("=" * 80)

        return stats