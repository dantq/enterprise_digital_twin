"""Database Sandbox and Security Enforcement for AI Analyst.

Enforces:
1. Strict Least-Privilege Execution:
   - Sets session role to `edt_ai_analyst` for all investigative agents.
   - Prevents access to hidden ground-truth tables (incidents, causal_*, benchmark_*).
2. Read-Only Transaction Enforcement:
   - All analyst queries run in read-only mode.
3. Evaluator Connection:
   - Evaluator runs under administrative privileges to read benchmark targets for scoring.
"""

from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional
import psycopg
from psycopg.rows import dict_row

from ai_analyst.config import (
    DB_HOST,
    DB_PORT,
    DB_NAME,
    DB_USER,
    DB_PASSWORD,
    ANALYST_ROLE,
)


@contextmanager
def get_analyst_connection():
    """Returns a connection sandboxed to the `edt_ai_analyst` role.
    
    Any attempt by an agent to query hidden ground-truth tables
    will result in an InsufficientPrivilege exception raised by PostgreSQL.
    """
    conn = psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        row_factory=dict_row,
    )
    try:
        # Enforce read-only session and impersonate restricted role
        with conn.cursor() as cur:
            cur.execute(f"SET ROLE {ANALYST_ROLE};")
            cur.execute("SET TRANSACTION READ ONLY;")
        yield conn
    finally:
        conn.close()


@contextmanager
def get_evaluator_connection():
    """Returns an administrative connection for the Benchmark Evaluation Engine ONLY.
    
    This is strictly prohibited for investigative agents and is only called
    by the Benchmark Scoring Engine after the AI Analyst report is completed.
    """
    conn = psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        row_factory=dict_row,
    )
    try:
        yield conn
    finally:
        conn.close()


def execute_analyst_query(sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
    """Executes a SELECT query under the secure analyst role and returns dict rows."""
    with get_analyst_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()


def get_incident_observations() -> List[Dict[str, Any]]:
    """Queries the safe projection view `ai_incident_observations`.
    
    Hides `scenario_id` to prevent ground-truth leakage while exposing
    observable surface symptoms, timestamps, severity, and domain.
    """
    sql = """
        SELECT 
            incident_id,
            detected_at,
            start_time,
            end_time,
            severity,
            affected_domain,
            status,
            surface_symptoms
        FROM ai_incident_observations
        ORDER BY detected_at ASC;
    """
    return execute_analyst_query(sql)
