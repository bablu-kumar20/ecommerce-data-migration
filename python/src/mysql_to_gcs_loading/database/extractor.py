import pandas as pd


def extract_table(mysql_engine, table_name):
    query = f"SELECT * FROM `{table_name}`"

    dataframe = pd.read_sql(query, mysql_engine)

    return dataframe