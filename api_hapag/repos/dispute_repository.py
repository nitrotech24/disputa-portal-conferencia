# api_hapag/repos/dispute_repository.py

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta
from api_hapag.config.db import get_conn


@dataclass(frozen=True)
class Disputa:
    id: int
    invoice_id: int
    dispute_number: int
    status: str
    dispute_reason: Optional[str] = None
    disputed_amount: Optional[float] = None
    currency: Optional[str] = None
    allow_second_review: Optional[bool] = None
    api_created_date: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ===== CONSTANTE: Status finais que NÃO devem ser atualizados =====
STATUS_FINAIS = ['ACCEPTED', 'REJECTED', 'CLOSED', 'CANCELLED']


# ===== NOVA FUNÇÃO: Buscar disputas antigas =====
def get_disputas_para_atualizar() -> List[Disputa]:
    """
    Retorna disputas que precisam ser atualizadas:
    - updated_at > 2 horas atrás
    - status NÃO está em STATUS_FINAIS
    - invoice é HAPAG
    """
    duas_horas_atras = datetime.now() - timedelta(hours=2)

    sql = """
        SELECT d.id, d.invoice_id, d.dispute_number, d.status,
               d.dispute_reason, d.disputed_amount, d.currency,
               d.allow_second_review,
               d.api_created_date, d.updated_at
        FROM disputa d
        JOIN invoice i ON d.invoice_id = i.id
        WHERE i.armador = 'HAPAG'
          AND d.updated_at < %s
          AND d.status NOT IN ({})
        ORDER BY d.updated_at ASC
    """.format(','.join(['%s'] * len(STATUS_FINAIS)))

    params = [duas_horas_atras] + STATUS_FINAIS

    with get_conn() as conn, conn.cursor(dictionary=True) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()
        return [Disputa(**row) for row in rows]


def get_disputa_by_invoice(invoice_id: int) -> Optional[Disputa]:
    sql = "SELECT * FROM disputa WHERE invoice_id = %s"
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
        cur.execute(sql_check, (invoice_id, status))
        row = cur.fetchone()
        if row:
            return None

        cur.execute(sql_insert, (invoice_id, status))
        conn.commit()
        return cur.lastrowid


# ===== FUNÇÃO MELHORADA: upsert com todos os campos =====
def upsert_disputa(invoice_id: int, dispute_number: int, data: dict) -> int:
    """
    Insere ou atualiza disputa com TODOS os dados da API.

    Args:
        invoice_id: ID da invoice no banco
        dispute_number: Número da disputa na Hapag
        data: Dicionário com dados da API completos

    Returns:
        ID da disputa inserida/atualizada
    """
    sql_check = """
        SELECT id, status FROM disputa
        WHERE invoice_id = %s AND dispute_number = %s
        LIMIT 1
    """

    sql_insert = """
        INSERT INTO disputa (
            invoice_id, dispute_number, status, dispute_reason,
            disputed_amount, currency, allow_second_review,
            api_created_date
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    sql_update = """
        UPDATE disputa
        SET status = %s,
            dispute_reason = %s,
            disputed_amount = %s,
            currency = %s,
            allow_second_review = %s,
            api_created_date = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """

    with get_conn() as conn, conn.cursor(dictionary=True) as cur:
        # Verifica se já existe
        cur.execute(sql_check, (invoice_id, dispute_number))
        row = cur.fetchone()

        if row:
            # Já existe - atualiza
            cur.execute(sql_update, (
                data.get('status'),
                data.get('dispute_reason'),
                data.get('amount'),
                data.get('currency'),
                data.get('allowSecondReview'),
                data.get('disputeCreated'),
                row["id"]
            ))
            conn.commit()
            return row["id"]

        # Não existe - insere
        cur.execute(sql_insert, (
            invoice_id,
            dispute_number,
            data.get('status'),
            data.get('dispute_reason'),
            data.get('amount'),
            data.get('currency'),
            data.get('allowSecondReview'),
            data.get('disputeCreated')
        ))
        conn.commit()
        return cur.lastrowid


# ===== NOVA FUNÇÃO: Atualizar disputa completa =====
def update_disputa_completa(disputa_id: int, data: dict) -> None:
    """
    Atualiza todos os campos de uma disputa existente.
    Usado quando a disputa já existe e precisa de refresh dos dados da API.
    """
    sql = """
        UPDATE disputa
        SET status = %s,
            dispute_reason = %s,
            disputed_amount = %s,
            currency = %s,
            allow_second_review = %s,
            api_created_date = %s,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (
            data.get('status'),
            data.get('dispute_reason'),
            data.get('amount'),
            data.get('currency'),
            data.get('allowSecondReview'),
            data.get('disputeCreated'),
            disputa_id
        ))
        conn.commit()


def update_disputa_status(disputa_id: int, status: str) -> None:
    """
    Atualiza apenas o status de uma disputa existente no banco.
    """
    sql = """
        UPDATE disputa
        SET status = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
    """
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (status, disputa_id))
        conn.commit()