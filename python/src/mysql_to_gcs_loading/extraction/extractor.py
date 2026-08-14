import pandas as pd


def extract_table(connection, table_name):
    query = f"SELECT * FROM `{table_name}`"

    dataframe = pd.read_sql(query, connection)

    return dataframe