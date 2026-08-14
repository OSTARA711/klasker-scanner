# ~/klasker-scanner/src/database.py

"""TiDB database connection and persistence for Klasker Scanner."""

import json
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


def create_schema():
    """Create the initial Klasker Scanner database schema."""

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scans (
                id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                requested_url VARCHAR(2048) NOT NULL,
                final_url VARCHAR(2048),
                domain VARCHAR(255),
                scanned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                http_status INT,
                score INT,
                result_json JSON NOT NULL,
                PRIMARY KEY (id),
                INDEX idx_scans_domain (domain),
                INDEX idx_scans_score (score),
                INDEX idx_scans_scanned_at (scanned_at)
            )
            """
        )

        connection.commit()

    finally:
        connection.close()


def save_scan(result):
    """Save one completed scanner result to TiDB."""

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO scans (
                requested_url,
                final_url,
                domain,
                http_status,
                score,
                result_json
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                result["target"]["requested_url"],
                result["target"]["final_url"],
                result["target"]["domain"],
                result["http"]["status"],
                result["score"]["score"],
                json.dumps(result),
            ),
        )

        connection.commit()

        return cursor.lastrowid

    finally:
        connection.close()


def get_scan(scan_id):
    """Retrieve one complete scanner result from TiDB by scan ID."""

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT result_json
            FROM scans
            WHERE id = %s
            """,
            (scan_id,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        result = row[0]

        if isinstance(result, str):
            result = json.loads(result)

        return result

    finally:
        connection.close()


def get_latest_scan(domain):
    """Retrieve the latest complete scanner result for a domain."""

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT result_json
            FROM scans
            WHERE domain = %s
            ORDER BY scanned_at DESC, id DESC
            LIMIT 1
            """,
            (domain,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        result = row[0]

        if isinstance(result, str):
            result = json.loads(result)

        return result

    finally:
        connection.close()


def get_latest_scan_metadata(domain):
    """Retrieve metadata for the latest scan of a domain."""

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id, domain, scanned_at, score
            FROM scans
            WHERE domain = %s
            ORDER BY scanned_at DESC, id DESC
            LIMIT 1
            """,
            (domain,),
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return {
            "id": row[0],
            "domain": row[1],
            "scanned_at": row[2],
            "score": row[3],
        }

    finally:
        connection.close()


def test_connection():
    """Open and close a TiDB connection."""

    connection = get_connection()

    try:
        print("TiDB connection successful.")

    finally:
        connection.close()


if __name__ == "__main__":
    create_schema()
    print("TiDB schema ready.")
