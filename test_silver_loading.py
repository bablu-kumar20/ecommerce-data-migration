from python.src.bigquery.client import create_bigquery_client
from python.src.bigquery.processor import (
    create_silver_products,
    create_silver_customers,
    create_silver_orders,
    create_silver_order_items,
)
from python.src.config import GCP_PROJECT_ID


def main():
    bigquery_client = create_bigquery_client()

    # Testing customer 

    # create_silver_customers(
    #     bigquery_client,
    #     GCP_PROJECT_ID,
    # )

    # Testing for Products

    # create_silver_products(
    #     bigquery_client,
    #     GCP_PROJECT_ID,
    # )

    # Testing for Orders

    # create_silver_orders(
    #     bigquery_client,
    #     GCP_PROJECT_ID,
    # )
    
    create_silver_order_items(
        bigquery_client,
        GCP_PROJECT_ID,
    )

if __name__ == "__main__":
    main()