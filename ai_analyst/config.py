"""Configuration settings for AI Analyst Multi-Agent System."""

import os

# PostgreSQL Database Configuration
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 5432))
DB_NAME = os.environ.get("DB_NAME", "enterprise_digital_twin_test")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("PGPASSWORD") or os.environ.get("DB_PASSWORD") or "Dantq24@#@#"

# Database Security Roles
# Agents ALWAYS query under this restricted role
ANALYST_ROLE = "edt_ai_analyst"

# Ground Truth Evaluator connects under admin role
EVALUATOR_USER = "postgres"

# Operational Constants
DEFAULT_TIMEZONE = "Asia/Bangkok"

# Heuristic thresholds for anomaly confirmation
PAYMENT_FAILURE_SPIKE_THRESHOLD = 0.40  # >40% failure rate indicates gateway/method anomaly
OVERDUE_PO_THRESHOLD = 1                # >=1 overdue PO in key supplier indicates disruption
STOCKOUT_TICKET_THRESHOLD = 3           # >=3 stockout complaints indicate fulfillment bottleneck
REVENUE_LOSS_TOLERANCE = 0.20           # 20% tolerance in financial impact evaluation
