import mysql.connector
from config.settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from utils.logger import setup_logger

logger = setup_logger(__name__)


def _conn():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


class DisputaRepository:
    def insert_or_update(
            self,
            invoice_id: int,
            dispute_number: int,
            status: str,
            disputed_amount: float = None,
            currency: str = None,
            reason_code: str = None,
            reason_description: str = None,
            dispute_type: str = None,
            invoice_due_date: str = None,
            agent_name: str = None,
            agent_email: str = None,
            status_code: str = None,
            api_created_date: str = None,
            api_last_modified: str = None,
            customer_code: str = None
    ):
        """
        Insere ou atualiza disputa para uma invoice com TODOS os campos disponíveis.
        """
        sql = """
        INSERT INTO disputa (
            invoice_id, 
            dispute_number, 
            status,
            disputed_amount,
            currency,
            reason_code,
            reason_description,
            dispute_type,
            invoice_due_date,
            agent_name,
            agent_email,
            status_code,
            api_created_date,
            api_last_modified,
            customer_code
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
          status = VALUES(status),
          disputed_amount = VALUES(disputed_amount),
          currency = VALUES(currency),
          reason_code = VALUES(reason_code),
          reason_description = VALUES(reason_description),
          dispute_type = VALUES(dispute_type),
          invoice_due_date = VALUES(invoice_due_date),
          agent_name = VALUES(agent_name),
          agent_email = VALUES(agent_email),
          status_code = VALUES(status_code),
          api_created_date = VALUES(api_created_date),
          api_last_modified = VALUES(api_last_modified),
          customer_code = VALUES(customer_code),
          updated_at = CURRENT_TIMESTAMP(3);
        """

        with _conn() as conn:
            cur = conn.cursor()
            cur.execute(sql, (
                invoice_id,
                dispute_number,
                status,
                disputed_amount,
                currency,
                reason_code,
                reason_description,
                dispute_type,
                invoice_due_date,
                agent_name,
                agent_email,
                status_code,
                api_created_date,
                api_last_modified,
                customer_code
            ))
            conn.commit()

            logger.info(
                f"Disputa {dispute_number} salva/atualizada para invoice_id={invoice_id} | "
                f"Status: {status} | Valor: {currency} {disputed_amount} | "
                f"Motivo: {reason_description}"
            )