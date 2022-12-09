from __future__ import annotations

import pathlib
from datetime import datetime, timedelta

from airflow.models import DAG
from pandas import DataFrame
from sqlalchemy import Column, types

from astro import sql as aql
from astro.files import File
from astro.table import Metadata, Table

CWD = pathlib.Path(__file__).parent
DATA_DIR = str(CWD) + "/../tests/data/"

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": 0,
}

dag = DAG(
    dag_id="example_merge_bigquery",
    start_date=datetime(2019, 1, 1),
    max_active_runs=3,
    schedule_interval=timedelta(minutes=30),
    default_args=default_args,
)


@aql.transform
def sample_create_table(input_table: Table):
    return "SELECT * FROM {{input_table}} LIMIT 10"


@aql.dataframe(columns_names_capitalization="original")
def my_df_func(input_df: DataFrame):
    print(input_df)


with dag:
    # [START merge_load_file_with_primary_key_example]
    target_table_1 = aql.load_file(
        input_file=File(DATA_DIR + "sample.csv"),
        output_table=Table(
            conn_id="bigquery",
            metadata=Metadata(schema="first_table_schema"),
            columns=[
                Column(name="id", type_=types.Integer, primary_key=True),
                Column(name="name", type_=types.String),
            ],
        ),
    )
    # [END merge_load_file_with_primary_key_example]
    target_table_2 = aql.load_file(
        input_file=File(DATA_DIR + "sample.csv"),
        output_table=Table(
            conn_id="bigquery",
            metadata=Metadata(schema="first_table_schema"),
            columns=[
                Column(name="id", type_=types.Integer, primary_key=True),
                Column(name="name", type_=types.String),
            ],
        ),
    )
    source_table = aql.load_file(
        input_file=File(DATA_DIR + "sample_part2.csv"),
        output_table=Table(
            conn_id="bigquery",
            metadata=Metadata(schema="second_table_schema"),
        ),
    )
    # [START merge_col_list_example]
    aql.merge(
        target_table=target_table_1,
        source_table=source_table,
        target_conflict_columns=["id"],
        columns=["id", "name"],
        if_conflicts="update",
    )
    # [END merge_col_list_example]

    # [START merge_col_dict_example]
    aql.merge(
        target_table=target_table_2,
        source_table=source_table,
        target_conflict_columns=["id"],
        columns={"id": "id", "name": "name"},
        if_conflicts="update",
    )
    # [END merge_col_dict_example]

    aql.cleanup()
