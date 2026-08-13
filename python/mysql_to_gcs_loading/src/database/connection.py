import mysql.connector

from config import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_DATABASE,
    MYSQL_USER,
    MYSQL_PASSWORD,
)

def create_mysql_connection():
    connection = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        database=MYSQL_DATABASE,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
    )

    return connection

def get_tables(connection):
    cursor = connection.cursor()

    cursor.execute("SHOW TABLES")

    tables = [row[0] for row in cursor.fetchall()]

    cursor.close()

    return tables

def get_table_row_count(connection, table_name):
    cursor = connection.cursor()

    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")

    count = cursor.fetchone()[0]

    cursor.close()

    return count