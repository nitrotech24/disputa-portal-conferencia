from dataclasses import dataclass
from typing import List
from api_hapag.db import get_conn

@dataclass(frozen=True)
class Invoice:
    id: int
    numero_invoice: str

def list_invoices(limit: int = 10) -> List[Invoice]:
    sql = """
        SELECT id, numero_invoice
        FROM invoice
        ORDER BY id
        LIMIT %s
    """
    with get_conn() as conn, conn.cursor(dictionary=True) as cur:
        cur.execute(sql, (limit,))
        rows = cur.fetchall()
        return [Invoice(id=row["id"], numero_invoice=row["numero_invoice"]) for row in rows]
def get_invoice_by_id(invoice_id: int):
    """
    Busca uma invoice pelo ID no banco.
    """
    from api_hapag.db import get_conn
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT id, numero_invoice FROM invoices WHERE id = %s", (invoice_id,))
    row = cur.fetchone()
    conn.close()

    if row:
        class Invoice:
            def __init__(self, id, numero_invoice):
                self.id = id
                self.numero_invoice = numero_invoice
        return Invoice(row["id"], row["numero_invoice"])
    return None
