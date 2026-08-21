from sqlalchemy import create_engine

from python.src.config import (
    MYSQL_HOST,
    MYSQL_PORT,
    MYSQL_DATABASE,
    MYSQL_USER,
    MYSQL_PASSWORD,
)


def create_mysql_connection():
    connection_url = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
    )

    engine = create_engine(connection_url)

    return engine
# def create_mysql_connection():
#     connection = mysql.connector.connect(
#         host=MYSQL_HOST,
#         port=MYSQL_PORT,
#         database=MYSQL_DATABASE,
#         user=MYSQL_USER,
#         password=MYSQL_PASSWORD,
#     )

#     return connection
