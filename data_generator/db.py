import os
import getpass
import psycopg
from psycopg.rows import dict_row

from config import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
)


def get_connection():
    password = os.environ.get("PGPASSWORD") or os.environ.get("DB_PASSWORD") or "Dantq24@#@#"
    if not password:
        password = getpass.getpass(
            f"Password for user {DB_USER}: "
        )

    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=password,
        row_factory=dict_row,
    )