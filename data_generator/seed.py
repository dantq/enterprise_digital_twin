from db import get_connection


def test_connection():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT current_database(), current_user;")
            database, user = cur.fetchone()

            print(f"Database: {database}")
            print(f"User: {user}")
            print("Connection: OK")


if __name__ == "__main__":
    test_connection()
