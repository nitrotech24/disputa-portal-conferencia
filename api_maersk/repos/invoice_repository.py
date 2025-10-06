import mysql.connector
from typing import List, Dict
from api_maersk.config.settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


def _conn():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


class InvoiceRepository:
    def fetch_invoices_maersk(self, limit: int = 20) -> List[Dict]:
        """
        Busca invoices do armador MAERSK
        """
        sql = """
        SELECT id, numero_invoice
        FROM invoice
        WHERE armador = 'MAERSK'
        LIMIT %s
        """
        with _conn() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, (limit,))
            return cur.fetchall()

    def fetch_invoices_by_customer(self, customer_code: str, limit: int = 1000) -> List[Dict]:
        """
        Busca invoices de um cliente específico
        """
        sql = """
        SELECT id, numero_invoice, customer_code
        FROM invoice
        WHERE armador = 'MAERSK' 
        AND customer_code = %s
        LIMIT %s
        """
        with _conn() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute(sql, (customer_code, limit))
            return cur.fetchall()