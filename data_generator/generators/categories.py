import random
from datetime import date

from db import get_connection
from config import SEED, CATEGORIES


CATEGORY_NAMES = [
    "Điện thoại",
    "Laptop",
    "Máy tính bảng",
    "Thiết bị mạng",
    "Thiết bị lưu trữ",
    "Phụ kiện máy tính",
    "Phụ kiện điện thoại",
    "Thiết bị văn phòng",
    "Màn hình",
    "Thiết bị âm thanh",
    "Camera",
    "Thiết bị gia dụng",
    "Đồ điện tử",
    "Thiết bị thông minh",
    "Phụ kiện ô tô",
    "Thiết bị chiếu sáng",
    "Cáp và sạc",
    "Thiết bị bảo mật",
    "Thiết bị POS",
    "Thiết bị kho",
    "Văn phòng phẩm",
    "Nội thất văn phòng",
    "Thiết bị hội nghị",
    "Thiết bị giáo dục",
    "Thiết bị công nghiệp",
    "Linh kiện điện tử",
    "Phần mềm",
    "Dịch vụ kỹ thuật",
    "Bảo hành",
    "Khác",
]


def generate_categories():
    random.seed(SEED)

    rows = []

    # Root categories
    for i in range(CATEGORIES):
        name = CATEGORY_NAMES[i % len(CATEGORY_NAMES)]

        if i >= len(CATEGORY_NAMES):
            name = f"{name} {i + 1}"

        rows.append(
            (
                name,
                None,
                "Active",
            )
        )

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO categories
                    (category_name, parent_category_id, status)
                VALUES
                    (%s, %s, %s)
                """,
                rows,
            )

        conn.commit()

    print(f"Inserted categories: {len(rows)}")


if __name__ == "__main__":
    generate_categories()
