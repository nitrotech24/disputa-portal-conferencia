from api_maersk.services.dispute_service import DisputeService
from api_maersk.repos.invoice_repository import InvoiceRepository
from api_maersk.repos.disputa_repository import DisputaRepository
from api_maersk.utils.logger import setup_logger
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import time

logger = setup_logger(__name__)


class DisputeSyncServiceParallel:
    def __init__(
            self,
            dispute_service: DisputeService,
            invoice_repo: InvoiceRepository,
            disputa_repo: DisputaRepository,
            max_workers: int = 10
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

                logger.info(f"Invoice {numero_invoice} tem disputa {dispute_id} (Cliente: {customer_code})")

                # BUSCAR DETALHES COMPLETOS DA DISPUTA
                dispute_details = self.dispute_service.get_dispute_details(dispute_id, customer_code)

                # DELAY PARA NÃO SOBRECARREGAR A API
                time.sleep(0.5)

                if dispute_details:
                    # Extrair TODOS os campos disponíveis
                    status = dispute_details.get("statusDescription", "Unknown")
                    disputed_amount = dispute_details.get("disputedAmount")
                    currency = dispute_details.get("currency")
                    api_created_date = dispute_details.get("createdDate")
                    api_last_modified = dispute_details.get("lastModifiedDate")

                    # Dispute Type
                    dispute_type = dispute_details.get("disputeType")

                    # Invoice Due Date
                    invoice_due_date = dispute_details.get("invoiceDueDate")

                    # Status Code
                    status_code = dispute_details.get("statusCode")

                    # Reason - pode ser objeto ou string
                    dispute_reason_obj = dispute_details.get("disputeReason")
                    if isinstance(dispute_reason_obj, dict):
                        reason_code = dispute_reason_obj.get("reasonCode")
                        reason_description = dispute_reason_obj.get("reasonDescription")
                    elif isinstance(dispute_reason_obj, str):
                        reason_code = None
                        reason_description = dispute_reason_obj
                    else:
                        reason_code = None
                        reason_description = None

                    # Agent info
                    agent_obj = dispute_details.get("agent")
                    if isinstance(agent_obj, dict):
                        agent_name = agent_obj.get("name") or agent_obj.get("agentName")
                        agent_email = agent_obj.get("email") or agent_obj.get("agentEmail")
                    else:
                        agent_name = None
                        agent_email = None

                    # Salvar COM TODOS OS CAMPOS
                    self.disputa_repo.insert_or_update(
                        invoice_id=invoice_id,
                        dispute_number=int(dispute_id),
                        status=status,
                        disputed_amount=disputed_amount,
                        currency=currency,
                        reason_code=reason_code,
                        reason_description=reason_description,
                        dispute_type=dispute_type,
                        invoice_due_date=invoice_due_date,
                        agent_name=agent_name,
                        agent_email=agent_email,
                        status_code=status_code,
                        api_created_date=api_created_date,
                        api_last_modified=api_last_modified,
                        customer_code=customer_code
                    )

                    result["has_dispute"] = True
                    result["success"] = True
                    result["dispute_id"] = dispute_id
                    result["status"] = status
                else:
                    logger.warning(f"Nao conseguiu buscar detalhes da disputa {dispute_id}")
                    result["error"] = "Failed to get dispute details"
            else:
                logger.info(f"Invoice {numero_invoice} sem disputa no cliente {customer_code}")
                result["success"] = True

        except Exception as e:
            logger.error(f"Erro ao processar invoice {numero_invoice}: {e}")
            result["error"] = str(e)

        return result

    def sync_disputes_parallel(self, customer_code: str, limit: int = 20):
        """
        Sincroniza disputas EM PARALELO.
        """
        logger.info(f"Iniciando sincronizacao PARALELA de disputas para {customer_code}")
        logger.info(f"Usando {self.max_workers} threads simultaneas")

        # 1. Buscar TODAS as disputas da API
        logger.info("Buscando todas as disputas da API...")
        all_disputes = self.dispute_service.list_all_disputes(customer_code)

        if not all_disputes:
            logger.warning("Nenhuma disputa encontrada na API")
            return {"erro": "Nenhuma disputa na API"}

        logger.info(f"Encontradas {len(all_disputes)} disputas na API")

        # 2. Criar mapa: invoiceNumber -> dispute
        dispute_map = {}
        for dispute in all_disputes:
            invoice_num = dispute.get("invoiceNumber")
            if invoice_num:
                dispute_map[invoice_num] = dispute

        logger.info(f"Mapa criado com {len(dispute_map)} invoices unicas")

        # 3. Buscar invoices MAERSK do banco
        invoices = self.invoice_repo.fetch_invoices_by_customer(customer_code, limit=limit)
        logger.info(f"Encontradas {len(invoices)} invoices no banco")

        if not invoices:
            logger.warning("Nenhuma invoice encontrada no banco")
            return {"erro": "Nenhuma invoice no banco"}

        stats = {
            "total_invoices": len(invoices),
            "com_disputa": 0,
            "sem_disputa": 0,
            "disputas_salvas": 0,
            "erros": 0
        }

        # 4. PROCESSAR EM PARALELO
        logger.info(f"Processando {len(invoices)} invoices em paralelo...")

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
                    logger.error(f"Erro: {result['error']}")

        # Retornar status
        logger.info("=" * 80)
        logger.info("SINCRONIZACAO PARALELA CONCLUIDA")
        logger.info("=" * 80)
        logger.info(f"Total de invoices: {stats['total_invoices']}")
        logger.info(f"Com disputa: {stats['com_disputa']}")
        logger.info(f"Sem disputa: {stats['sem_disputa']}")
        logger.info(f"Disputas salvas: {stats['disputas_salvas']}")
        logger.info(f"Erros: {stats['erros']}")
        logger.info("=" * 80)

        return stats