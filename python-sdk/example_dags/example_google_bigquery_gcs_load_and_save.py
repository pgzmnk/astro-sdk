"""
This Example DAG:
 - Pulls a CSV file from Github and loads it into BigQuery.
 - Extracts the data from BigQuery and load into in-memory Pandas Dataframe
 - Finds the Top 5 movies based on rating using pandas dataframe
 - And loads it into a Google Cloud Storage bucket in a CSV file

Pre-requisites:
 - Install dependencies for Astro Python SDK with Google, refer to README.md
 - Create an Airflow Connection to connect to Bigquery Table. Example:
    export AIRFLOW_CONN_BIGQUERY="bigquery://astronomer-dag-authoring"
 - You can either specify a service account key file and set `GOOGLE_APPLICATION_CREDENTIALS`
    with the file path to the service account.
"""
from __future__ import annotations

import os

import pandas as pd
from airflow.models.dag import DAG
from airflow.utils import timezone

import astro.sql as aql
from astro.files import File
from astro.table import Metadata, Table

with DAG(
    dag_id="example_google_bigquery_gcs_load_and_save",
    schedule_interval=None,
    start_date=timezone.datetime(2022, 1, 1),
) as dag:
    # [START load_file_http_example]
    t1 = aql.load_file(
        task_id="load_from_github_to_bq",
        input_file=File(
            path="https://raw.githubusercontent.com/astronomer/astro-sdk/main/tests/data/imdb_v2.csv"
        ),
        output_table=Table(name="imdb_movies", conn_id="bigquery", metadata=Metadata(schema="astro")),
    )
    # [END load_file_http_example]

    # Setting "identifiers_as_lower" to True will lowercase all column names
    @aql.dataframe(columns_names_capitalization="original")
    def extract_top_5_movies(input_df: pd.DataFrame):
        print(f"Total Number of records: {len(input_df)}")
        top_5_movies = input_df.sort_values(by="rating", ascending=False)[["title", "rating", "genre1"]].head(
            5
        )
        print(f"Top 5 Movies: {top_5_movies}")
        return top_5_movies

    t2 = extract_top_5_movies(input_df=t1)

    # [START export_example_1]
    gcs_bucket = os.getenv("GCS_BUCKET", "gs://dag-authoring")

    aql.export_file(
        task_id="save_file_to_gcs",
        input_data=t1,
        output_file=File(
            path=f"{gcs_bucket}/{{{{ task_instance_key_str }}}}/all_movies.csv",
            conn_id="gcp_conn",
        ),
        if_exists="replace",
    )
    # [END export_example_1]

    # [START export_example_2]
    aql.export_file(
        task_id="save_dataframe_to_gcs",
        input_data=t2,
        output_file=File(
            path=f"{gcs_bucket}/{{{{ task_instance_key_str }}}}/top_5_movies.csv",
            conn_id="gcp_conn",
        ),
        if_exists="replace",
    )
    # [END export_example_2]

    aql.cleanup()
