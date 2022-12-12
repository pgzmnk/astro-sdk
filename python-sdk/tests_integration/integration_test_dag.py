import pathlib

import pandas as pd
import pytest
from airflow.decorators import task, task_group
from airflow.utils import timezone

from astro import sql as aql
from astro.constants import Database
from astro.databases import create_database
from astro.files import File
from astro.table import Table
from tests.sql.operators import utils as test_utils

OUTPUT_TABLE_NAME = test_utils.get_table_name("integration_test_table")

DEFAULT_DATE = timezone.datetime(2016, 1, 1)

CWD = pathlib.Path(__file__).parent

default_args = {
    "owner": "airflow",
    "retries": 1,
    "retry_delay": 0,
}


@aql.transform
def apply_transform(input_table: Table):
    return "SELECT * FROM {{input_table}}"


@aql.dataframe
def do_a_dataframe_thing(df: pd.DataFrame):
    return df


@aql.dataframe
def count_dataframes(df1: pd.DataFrame, df2: pd.DataFrame):
    return len(df1) + len(df2)


@task
def compare(a, b):
    assert a == b


@task_group
def run_dataframe_funcs(input_table: Table):
    table_counts = count_dataframes(df1=input_table, df2=input_table)

    df1 = do_a_dataframe_thing(input_table)
    df2 = do_a_dataframe_thing(input_table)
    df_counts = count_dataframes(df1, df2)
    compare(table_counts, df_counts)


@aql.run_raw_sql
def add_constraint(table: Table):
    db = create_database(table.conn_id)
    constraints = ("list", "sell")
    return db.get_merge_initialization_query(parameters=constraints)


@task_group
def run_append(output_table: Table):
    load_main = aql.load_file(
        input_file=File(path=str(CWD) + "/data/homes_main.csv"),
        output_table=output_table,
    )
    load_append = aql.load_file(
        input_file=File(path=str(CWD) + "/data/homes_append.csv"),
        output_table=output_table.create_similar_table(),
    )

    aql.append(
        columns={"sell": "sell", "living": "living"},
        target_table=load_main,
        source_table=load_append,
    )


@task_group
def run_merge(output_table: Table):
    main_table = aql.load_file(
        input_file=File(path=str(CWD) + "/data/homes_merge_1.csv"),
        output_table=output_table,
    )
    merge_table = aql.load_file(
        input_file=File(path=str(CWD) + "/data/homes_merge_2.csv"),
        output_table=output_table.create_similar_table(),
    )

    con1 = add_constraint(main_table)

    merged_table = aql.merge(
        target_table=main_table,
        source_table=merge_table,
        target_conflict_columns=["list", "sell"],
        columns={"list": "list", "sell": "sell"},
        if_conflicts="ignore",
    )
    con1 >> merged_table  # skipcq PYL-W0104


@pytest.mark.parametrize(
    "database_table_fixture",
    [
        {"database": Database.SNOWFLAKE},
        {"database": Database.BIGQUERY},
        {"database": Database.POSTGRES},
        {"database": Database.SQLITE},
    ],
    indirect=True,
    ids=["snowflake", "bigquery", "postgresql", "sqlite"],
)
def test_full_dag(database_table_fixture, sample_dag):
    _, output_table = database_table_fixture
    with sample_dag:
        loaded_table = aql.load_file(
            input_file=File(path=str(CWD) + "/data/homes.csv"),
            output_table=output_table,
        )
        tranformed_table = apply_transform(loaded_table)
        run_dataframe_funcs(tranformed_table)
        run_append(output_table)
        run_merge(output_table)
        aql.export_file(
            input_data=tranformed_table,
            output_file=File(path="/tmp/out_agg.csv"),
            if_exists="replace",
        )
        aql.cleanup()
    test_utils.run_dag(sample_dag)
