import os
from contextlib import contextmanager
from mysql.connector import pooling
from dotenv import load_dotenv

load_dotenv()

_pool = pooling.MySQLConnectionPool(
    pool_name="hapag_pool",
    pool_size=5,
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASS", ""),
    database=os.getenv("DB_NAME", "feat_pc"),
)

@contextmanager
def get_conn():
    conn = _pool.get_connection()
    try:
        yield conn
    finally:
        conn.close()
