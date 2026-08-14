# ~/klasker-scanner/src/database.py

"""TiDB database connection for Klasker Scanner."""

import os

import mysql.connector
from dotenv import load_dotenv


load_dotenv()


def get_connection():
    """Create and return a TLS-secured TiDB connection."""

    return mysql.connector.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ["DB_PORT"]),
        user=os.environ["DB_USERNAME"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_DATABASE"],
        ssl_ca=os.environ["DB_CA"],
        ssl_verify_cert=True,
        ssl_verify_identity=True,
    )


def test_connection():
    """Open and close a TiDB connection."""

    connection = get_connection()

    try:
        print("TiDB connection successful.")

    finally:
        connection.close()


if __name__ == "__main__":
    test_connection()
