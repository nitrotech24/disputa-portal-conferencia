import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import mysql.connector
from config.settings import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
from tabulate import tabulate


def get_connection():
    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )


def view_recent_disputes(limit=20):
    """Mostra as disputas mais recentes"""
    print("\n" + "=" * 80)
    print("DISPUTAS MAIS RECENTES")
    print("=" * 80)

    sql = """
    SELECT 
        d.dispute_number,
        i.numero_invoice,
        d.status,
        d.disputed_amount,
        d.currency,
        d.customer_code,
        d.updated_at
    FROM disputa d
    JOIN invoice i ON d.invoice_id = i.id
    ORDER BY d.updated_at DESC
    LIMIT %s
    """

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql, (limit,))
        results = cur.fetchall()

        if results:
            headers = ["Disputa", "Invoice", "Status", "Valor", "Moeda", "Cliente", "Atualizado"]
            print(tabulate(results, headers=headers, tablefmt="grid"))
        else:
            print("Nenhuma disputa encontrada!")


def view_statistics():
    """Mostra estatísticas gerais"""
    print("\n" + "=" * 80)
    print("ESTATÍSTICAS")
    print("=" * 80)

    sql = """
    SELECT 
        COUNT(*) as total_disputas,
        COUNT(DISTINCT invoice_id) as invoices_com_disputa,
        SUM(disputed_amount) as valor_total_disputado
    FROM disputa
    """

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        result = cur.fetchone()

        print(f"\nTotal de disputas: {result[0]}")
        print(f"Invoices com disputa: {result[1]}")
        print(f"Valor total disputado: {result[2]}")

    # Por status
    sql = """
    SELECT 
        status,
        COUNT(*) as quantidade,
        SUM(disputed_amount) as valor_total
    FROM disputa
    GROUP BY status
    ORDER BY quantidade DESC
    """

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        results = cur.fetchall()

        if results:
            print("\nPor Status:")
            headers = ["Status", "Quantidade", "Valor Total"]
            print(tabulate(results, headers=headers, tablefmt="grid"))


def view_by_customer():
    """Mostra disputas por cliente"""
    print("\n" + "=" * 80)
    print("DISPUTAS POR CLIENTE")
    print("=" * 80)

    sql = """
    SELECT 
        customer_code,
        COUNT(*) as quantidade,
        SUM(disputed_amount) as valor_total
    FROM disputa
    WHERE customer_code IS NOT NULL
    GROUP BY customer_code
    ORDER BY quantidade DESC
    """

    with get_connection() as conn:
        cur = conn.cursor()
        cur.execute(sql)
        results = cur.fetchall()

        if results:
            headers = ["Cliente", "Quantidade", "Valor Total"]
            print(tabulate(results, headers=headers, tablefmt="grid"))


def main():
    print("\n" + "=" * 80)
    print("VISUALIZAÇÃO DO BANCO DE DADOS - DISPUTAS")
    print("=" * 80)

    view_statistics()
    view_by_customer()
    view_recent_disputes(20)

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()