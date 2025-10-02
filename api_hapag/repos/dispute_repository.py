# api_hapag/repos/disputa_repo.py

from dataclasses import dataclass
from typing import List, Optional
from api_hapag.config.db import get_conn

@dataclass(frozen=True)
class Disputa:
    id: int
    invoice_id: int
    status: str

def get_disputa_by_invoice(invoice_id: int) -> Optional[Disputa]:
    sql = "SELECT id, invoice_id, status FROM disputa WHERE invoice_id = %s"
    with get_conn() as conn, conn.cursor(dictionary=True) as cur:
        cur.execute(sql, (invoice_id,))
        row = cur.fetchone()
        if row:
            return Disputa(**row)
    return None

def insert_disputa(invoice_id: int, status: str) -> int:
    sql = "INSERT INTO disputa (invoice_id, status) VALUES (%s, %s)"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (invoice_id, status))
        conn.commit()
        return cur.lastrowid
def insert_disputa_if_not_exists(invoice_id: int, status: str) -> int | None:
    """
    Insere disputa apenas se não existir ainda para a mesma invoice + status.
    Retorna id da disputa se inseriu, ou None se já existia.
    """
    sql_check = """
        SELECT id FROM disputa
        WHERE invoice_id = %s AND status = %s
        LIMIT 1
    """
    sql_insert = """
        INSERT INTO disputa (invoice_id, status)
        VALUES (%s, %s)
    """
    with get_conn() as conn, conn.cursor(dictionary=True) as cur:
        # verifica se já existe
        cur.execute(sql_check, (invoice_id, status))
        row = cur.fetchone()
        if row:
            return None  # já existe no banco

        # se não existe, insere
        cur.execute(sql_insert, (invoice_id, status))
        conn.commit()
        return cur.lastrowid
def upsert_disputa(invoice_id: int, dispute_number: int, status: str) -> int:
    """
    Insere ou atualiza disputa conforme dispute_number.
    - Se não existir: cria.
    - Se já existir mas o status mudou: atualiza.
    Retorna o id da disputa.
    """
    sql_check = """
        SELECT id, status FROM disputa
        WHERE invoice_id = %s AND dispute_number = %s
        LIMIT 1
    """
    sql_insert = """
        INSERT INTO disputa (invoice_id, dispute_number, status)
        VALUES (%s, %s, %s)
    """
    sql_update = """
        UPDATE disputa
        SET status = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """

    with get_conn() as conn, conn.cursor(dictionary=True) as cur:
        # verifica se já existe
        cur.execute(sql_check, (invoice_id, dispute_number))
        row = cur.fetchone()

        if row:
            if row["status"] != status:
                cur.execute(sql_update, (status, row["id"]))
                conn.commit()
                return row["id"]  # retornamos o mesmo id
            return row["id"]  # já existe igual, nada muda

        # se não existe, insere
        cur.execute(sql_insert, (invoice_id, dispute_number, status))
        conn.commit()
        return cur.lastrowid
def update_disputa_status(disputa_id: int, status: str) -> None:
    """
    Atualiza o status de uma disputa existente no banco.
    """
    sql = """
        UPDATE disputa
        SET status = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (status, disputa_id))
        conn.commit()
