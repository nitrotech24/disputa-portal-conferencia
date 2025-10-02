from dataclasses import dataclass
from typing import List, Optional
from api_hapag.config.db import get_conn


@dataclass(frozen=True)
class Invoice:
    id: int
    numero_invoice: str


def list_invoices(limit: Optional[int] = None) -> List[Invoice]:
    """
    Lista invoices HAPAG do banco com limite configuravel.
    
    Args:
        limit: Numero maximo de invoices a retornar (None = todas)
        
    Returns:
        Lista de objetos Invoice apenas da HAPAG
    """
    if limit is None:
        sql = """
            SELECT id, numero_invoice
            FROM invoice
            WHERE armador = 'HAPAG'
            ORDER BY id
        """
        with get_conn() as conn, conn.cursor(dictionary=True) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
            return [Invoice(id=row["id"], numero_invoice=row["numero_invoice"]) for row in rows]
    else:
        sql = """
            SELECT id, numero_invoice
            FROM invoice
            WHERE armador = 'HAPAG'
            ORDER BY id
            LIMIT %s
        """
        with get_conn() as conn, conn.cursor(dictionary=True) as cur:
            cur.execute(sql, (limit,))
            rows = cur.fetchall()
            return [Invoice(id=row["id"], numero_invoice=row["numero_invoice"]) for row in rows]


def get_invoice_by_id(invoice_id: int) -> Optional[Invoice]:
    """
    Busca uma invoice HAPAG pelo ID no banco.
    
    Args:
        invoice_id: ID da invoice
        
    Returns:
        Objeto Invoice se encontrado e for HAPAG, None caso contrario
    """
    sql = """
        SELECT id, numero_invoice 
        FROM invoice 
        WHERE id = %s AND armador = 'HAPAG'
    """
    with get_conn() as conn, conn.cursor(dictionary=True) as cur:
        cur.execute(sql, (invoice_id,))
        row = cur.fetchone()
        if row:
            return Invoice(**row)
    return None