# Enterprise Digital Twin
# Data Generator Configuration

# PostgreSQL
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "enterprise_digital_twin_test"
DB_USER = "postgres"

# Reproducibility
SEED = 20260828

# Smoke-test dataset size
CATEGORIES = 30
CUSTOMERS = 100
SUPPLIERS = 20
WAREHOUSES = 5
CARRIERS = 5
PAYMENT_METHODS = 6
PRODUCTS = 100

# Supplier-product relationships
SUPPLIER_PRODUCTS_PER_PRODUCT_MIN = 1
SUPPLIER_PRODUCTS_PER_PRODUCT_MAX = 3
