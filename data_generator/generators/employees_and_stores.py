"""Generate and seed Stores and Employees entities into the Enterprise Digital Twin.

This script:
1. Creates `stores` and `employees` tables with full referential integrity.
2. Seeds 6 physical stores across key economic regions in Vietnam.
3. Seeds 30 realistic employees across Sales, Customer Service, and Store Management.
4. Alters `orders` table to add `store_id` and `employee_id`.
5. Alters `customer_tickets` table to add `assigned_employee_id`.
6. Distributes store and employee assignments across historical orders and tickets.
7. Grants SELECT permission to `edt_ai_analyst` for safe AI queries.
"""

import sys
import uuid
import random
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "data_generator"))
sys.path.insert(0, str(PROJECT_ROOT))

from db import get_connection

STORES_DATA = [
    ("ST-HN-01", "Chi nhánh Hoàn Kiếm", "Cửa hàng Flagship", "45 Tràng Tiền, P. Tràng Tiền, Q. Hoàn Kiếm", "Hà Nội", "Miền Bắc", "024-3825-1122"),
    ("ST-HN-02", "Chi nhánh Cầu Giấy", "Cửa hàng Tiêu chuẩn", "122 Xuân Thủy, P. Dịch Vọng Hậu, Q. Cầu Giấy", "Hà Nội", "Miền Bắc", "024-3754-3344"),
    ("ST-HCM-01", "Chi nhánh Quận 1", "Cửa hàng Flagship", "68 Nguyễn Huệ, P. Bến Nghé, Quận 1", "TP Hồ Chí Minh", "Miền Nam", "028-3822-5566"),
    ("ST-HCM-02", "Chi nhánh Tân Bình", "Cửa hàng Tiêu chuẩn", "345 Cộng Hòa, P. 13, Q. Tân Bình", "TP Hồ Chí Minh", "Miền Nam", "028-3810-7788"),
    ("ST-DN-01", "Chi nhánh Đà Nẵng", "Cửa hàng Khu vực", "180 Lê Duẩn, P. Thạch Thang, Q. Hải Châu", "Đà Nẵng", "Miền Trung", "0236-388-9900"),
    ("ST-CT-01", "Chi nhánh Cần Thơ", "Cửa hàng Khu vực", "56 Đại lộ Hòa Bình, P. An Cư, Q. Ninh Kiều", "Cần Thơ", "Miền Tây", "0292-381-2233"),
]

EMPLOYEES_DATA = [
    # Store Managers
    ("Nguyễn Văn Toàn", "StoreManager", "Kinh doanh Bán lẻ", "toan.nv@omnicorp.vn", "0903112233", "ST-HN-01"),
    ("Trần Thị Mai", "StoreManager", "Kinh doanh Bán lẻ", "mai.tt@omnicorp.vn", "0903223344", "ST-HN-02"),
    ("Lê Hoàng Nam", "StoreManager", "Kinh doanh Bán lẻ", "nam.lh@omnicorp.vn", "0903334455", "ST-HCM-01"),
    ("Phạm Minh Tuấn", "StoreManager", "Kinh doanh Bán lẻ", "tuan.pm@omnicorp.vn", "0903445566", "ST-HCM-02"),
    ("Hoàng Đức Thắng", "StoreManager", "Kinh doanh Bán lẻ", "thang.hd@omnicorp.vn", "0903556677", "ST-DN-01"),
    ("Võ Quốc Bảo", "StoreManager", "Kinh doanh Bán lẻ", "bao.vq@omnicorp.vn", "0903667788", "ST-CT-01"),

    # Sales Representatives (In-store & Key Account / Online Sales)
    ("Đặng Thanh Hương", "Sales", "Bán hàng Trực tiếp", "huong.dt@omnicorp.vn", "0912111222", "ST-HN-01"),
    ("Bùi Tiến Dũng", "Sales", "Bán hàng Trực tiếp", "dung.bt@omnicorp.vn", "0912222333", "ST-HN-01"),
    ("Đỗ Thị Phương", "Sales", "Bán hàng Trực tiếp", "phuong.dt@omnicorp.vn", "0912333444", "ST-HN-02"),
    ("Vũ Anh Khoa", "Sales", "Bán hàng Trực tiếp", "khoa.va@omnicorp.vn", "0912444555", "ST-HN-02"),
    ("Ngô Nhật Linh", "Sales", "Bán hàng Trực tiếp", "linh.nn@omnicorp.vn", "0912555666", "ST-HCM-01"),
    ("Phan Gia Hưng", "Sales", "Bán hàng Trực tiếp", "hung.pg@omnicorp.vn", "0912666777", "ST-HCM-01"),
    ("Trương Mỹ Duyên", "Sales", "Bán hàng Trực tiếp", "duyen.tm@omnicorp.vn", "0912777888", "ST-HCM-01"),
    ("Lý Khắc Cường", "Sales", "Bán hàng Trực tiếp", "cuong.lk@omnicorp.vn", "0912888999", "ST-HCM-02"),
    ("Dương Thảo Nhi", "Sales", "Bán hàng Trực tiếp", "nhi.dt@omnicorp.vn", "0912999000", "ST-HCM-02"),
    ("Hồ Văn Lộc", "Sales", "Bán hàng Trực tiếp", "loc.hv@omnicorp.vn", "0913111222", "ST-DN-01"),
    ("Lâm Ánh Nguyệt", "Sales", "Bán hàng Trực tiếp", "nguyet.la@omnicorp.vn", "0913222333", "ST-DN-01"),
    ("Mai Kim Oanh", "Sales", "Bán hàng Trực tiếp", "oanh.mk@omnicorp.vn", "0913333444", "ST-CT-01"),
    ("Tạ Đình Trọng", "Sales", "Bán hàng Trực tiếp", "trong.td@omnicorp.vn", "0913444555", "ST-CT-01"),
    ("Lê Hải Yến", "Sales", "Tư vấn Trực tuyến", "yen.lh@omnicorp.vn", "0913555666", None),
    ("Đinh Trọng Giáp", "Sales", "Tư vấn Trực tuyến", "giap.dt@omnicorp.vn", "0913666777", None),
    ("Trần Văn Phúc", "Sales", "Tư vấn Trực tuyến", "phuc.tv@omnicorp.vn", "0913777888", None),

    # Customer Service Agents
    ("Nguyễn Thu Trang", "CustomerService", "Chăm sóc Khách hàng", "trang.nt@omnicorp.vn", "0988111222", None),
    ("Lê Bảo Ngọc", "CustomerService", "Chăm sóc Khách hàng", "ngoc.lb@omnicorp.vn", "0988222333", None),
    ("Trần Minh Quân", "CustomerService", "Chăm sóc Khách hàng", "quan.tm@omnicorp.vn", "0988333444", None),
    ("Phạm Thùy Linh", "CustomerService", "Chăm sóc Khách hàng", "linh.pt@omnicorp.vn", "0988444555", None),
    ("Hoàng Lan Anh", "CustomerService", "Chăm sóc Khách hàng", "anh.hl@omnicorp.vn", "0988555666", None),

    # Warehouse & Operations Staff
    ("Vũ Đức Đạt", "WarehouseStaff", "Kho vận & Điều phối", "dat.vd@omnicorp.vn", "0977111222", None),
    ("Đoàn Quốc Tuấn", "WarehouseStaff", "Kho vận & Điều phối", "tuan.dq@omnicorp.vn", "0977222333", None),
    ("Nguyễn Xuân Hùng", "WarehouseStaff", "Kho vận & Điều phối", "hung.nx@omnicorp.vn", "0977333444", None),
]


def seed_stores_and_employees():
    print("=" * 70)
    print("SEEDING STORES & EMPLOYEES EXTENSION")
    print("=" * 70)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. Create table stores
            print("[1/7] Creating 'stores' table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stores (
                    store_id UUID PRIMARY KEY,
                    store_code VARCHAR(50) UNIQUE NOT NULL,
                    store_name VARCHAR(150) NOT NULL,
                    store_type VARCHAR(50) NOT NULL,
                    address TEXT NOT NULL,
                    city VARCHAR(50) NOT NULL,
                    region VARCHAR(50) NOT NULL,
                    phone VARCHAR(30),
                    status VARCHAR(30) DEFAULT 'Active',
                    opened_date DATE DEFAULT '2024-01-01',
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Create table employees
            print("[2/7] Creating 'employees' table...")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS employees (
                    employee_id UUID PRIMARY KEY,
                    store_id UUID REFERENCES stores(store_id),
                    full_name VARCHAR(150) NOT NULL,
                    role VARCHAR(50) NOT NULL,
                    department VARCHAR(100) NOT NULL,
                    email VARCHAR(150) UNIQUE NOT NULL,
                    phone VARCHAR(30),
                    status VARCHAR(30) DEFAULT 'Active',
                    hire_date DATE DEFAULT '2024-06-01',
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. Seed stores
            print("[3/7] Populating stores...")
            store_id_map = {}
            for code, name, stype, addr, city, reg, phone in STORES_DATA:
                cur.execute("SELECT store_id FROM stores WHERE store_code = %s", (code,))
                row = cur.fetchone()
                if row:
                    sid = row["store_id"]
                else:
                    sid = uuid.uuid4()
                    cur.execute("""
                        INSERT INTO stores (store_id, store_code, store_name, store_type, address, city, region, phone)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (sid, code, name, stype, addr, city, reg, phone))
                store_id_map[code] = sid
            print(f"      [OK] Seeded/Verified {len(store_id_map)} physical stores.")

            # 4. Seed employees
            print("[4/7] Populating employees...")
            sales_emp_ids = []
            cs_emp_ids = []
            for name, role, dept, email, phone, store_code in EMPLOYEES_DATA:
                sid = store_id_map.get(store_code) if store_code else None
                cur.execute("SELECT employee_id FROM employees WHERE email = %s", (email,))
                row = cur.fetchone()
                if row:
                    eid = row["employee_id"]
                else:
                    eid = uuid.uuid4()
                    cur.execute("""
                        INSERT INTO employees (employee_id, store_id, full_name, role, department, email, phone)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (eid, sid, name, role, dept, email, phone))

                if role in ("Sales", "StoreManager"):
                    sales_emp_ids.append((eid, sid))
                elif role == "CustomerService":
                    cs_emp_ids.append(eid)
            print(f"      [OK] Seeded/Verified {len(EMPLOYEES_DATA)} employees ({len(sales_emp_ids)} sales, {len(cs_emp_ids)} CS).")

            # 5. Alter orders and assign store_id, employee_id
            print("[5/7] Linking orders to stores and sales employees...")
            cur.execute("""
                ALTER TABLE orders 
                ADD COLUMN IF NOT EXISTS store_id UUID REFERENCES stores(store_id),
                ADD COLUMN IF NOT EXISTS employee_id UUID REFERENCES employees(employee_id);
            """)

            # Fetch orders that don't have store_id / employee_id set
            cur.execute("SELECT order_id, channel FROM orders")
            orders = cur.fetchall()
            rng = random.Random(42)

            store_orders_count = 0
            online_orders_count = 0
            for ord_row in orders:
                oid = ord_row["order_id"]
                channel = ord_row["channel"]

                if channel == "Store":
                    # Store order gets a physical store and a store sales rep
                    chosen_rep, chosen_sid = rng.choice([x for x in sales_emp_ids if x[1] is not None])
                    cur.execute("""
                        UPDATE orders 
                        SET store_id = %s, employee_id = %s 
                        WHERE order_id = %s AND (store_id IS NULL OR employee_id IS NULL)
                    """, (chosen_sid, chosen_rep, oid))
                    store_orders_count += 1
                else:
                    # Online order: 60% chance assigned to an online sales advisor, store_id is NULL
                    chosen_rep = rng.choice(sales_emp_ids)[0] if rng.random() < 0.70 else None
                    cur.execute("""
                        UPDATE orders 
                        SET employee_id = %s 
                        WHERE order_id = %s AND employee_id IS NULL
                    """, (chosen_rep, oid))
                    online_orders_count += 1

            print(f"      [OK] Linked orders: {store_orders_count} store orders and {online_orders_count} online orders.")

            # 6. Alter customer_tickets and assign employee_id
            print("[6/7] Linking customer_tickets to CS employees...")
            cur.execute("""
                ALTER TABLE customer_tickets 
                ADD COLUMN IF NOT EXISTS assigned_employee_id UUID REFERENCES employees(employee_id);
            """)

            cur.execute("SELECT ticket_id FROM customer_tickets WHERE assigned_employee_id IS NULL")
            unassigned_tickets = cur.fetchall()
            for t in unassigned_tickets:
                tid = t["ticket_id"]
                assigned_cs = rng.choice(cs_emp_ids)
                cur.execute("""
                    UPDATE customer_tickets 
                    SET assigned_employee_id = %s 
                    WHERE ticket_id = %s
                """, (assigned_cs, tid))
            print(f"      [OK] Assigned CS employees to {len(unassigned_tickets)} tickets.")

            # 7. Grant Permissions to edt_ai_analyst
            print("[7/7] Granting safe SELECT permissions on stores & employees to edt_ai_analyst...")
            cur.execute("GRANT SELECT ON stores TO edt_ai_analyst;")
            cur.execute("GRANT SELECT ON employees TO edt_ai_analyst;")
            print("      [OK] Permissions granted successfully!")

        conn.commit()

    print("=" * 70)
    print("STORES & EMPLOYEES SEEDING COMPLETED WITH 100% SUCCESS!")
    print("=" * 70)


if __name__ == "__main__":
    seed_stores_and_employees()
