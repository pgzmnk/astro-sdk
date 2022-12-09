from __future__ import annotations

import os
import pathlib
from unittest import mock

import pandas as pd
import pytest

from astro import sql as aql
from astro.airflow.datasets import DATASET_SUPPORT
from astro.constants import Database
from astro.files import File
from astro.sql.operators.append import AppendOperator
from astro.table import Metadata, Table
from tests.sql.operators import utils as test_utils
from tests.utils.airflow import create_context

CWD = pathlib.Path(__file__).parent


@aql.dataframe
def validate_basic(df: pd.DataFrame):
    assert len(df) == 6
    assert not df["sell"].hasnans
    assert df["rooms"].hasnans


@aql.dataframe
def validate_append_all(df: pd.DataFrame):
    assert len(df) == 6
    assert not df["sell"].hasnans
    assert not df["rooms"].hasnans


@aql.dataframe
def validate_caste_only(df: pd.DataFrame):
    assert len(df) == 6
    assert not df["age"].hasnans
    assert df["sell"].hasnans


@pytest.fixture
def append_params(request):
    mode = request.param
    if mode == "basic":
        return {
            "columns": {"sell": "sell", "living": "living"},
        }, validate_basic
    if mode == "all_fields":
        return {}, validate_append_all


@pytest.mark.parametrize(
    "test_columns,expected_columns",
    [
        (["sell", "list"], {"sell": "sell", "list": "list"}),
        (("sell", "list"), {"sell": "sell", "list": "list"}),
        (
            {"s_sell": "t_sell", "s_list": "t_list"},
            {"s_sell": "t_sell", "s_list": "t_list"},
        ),
    ],
)
def test_columns_params(test_columns, expected_columns):
    """
    Test that the columns param in AppendOperator takes list/tuple/dict and converts them to dict
    before sending over to db.append_table()
    """
    source_table = Table(name="source_table", conn_id="test1", metadata=Metadata(schema="test"))
    target_table = Table(name="target_table", conn_id="test2", metadata=Metadata(schema="test"))
    append_task = AppendOperator(
        source_table=source_table,
        target_table=target_table,
        columns=test_columns,
    )
    assert append_task.columns == expected_columns
    with mock.patch("astro.databases.base.BaseDatabase.append_table") as mock_append, mock.patch.dict(
        os.environ,
        {"AIRFLOW_CONN_TEST1": "sqlite://", "AIRFLOW_CONN_TEST2": "sqlite://"},
    ):
        append_task.execute(context=create_context(append_task))
        mock_append.assert_called_once_with(
            source_table=source_table,
            target_table=target_table,
            source_to_target_columns_map=expected_columns,
        )


def test_invalid_columns_param():
    """Test that an error is raised when an invalid columns type is passed"""
    source_table = Table(name="source_table", conn_id="test1", metadata=Metadata(schema="test"))
    target_table = Table(name="target_table", conn_id="test2", metadata=Metadata(schema="test"))
    with pytest.raises(ValueError) as exec_info:
        AppendOperator(
            source_table=source_table,
            target_table=target_table,
            columns={"set_item_1", "set_item_2", "set_item_3"},
        )
    assert (
        exec_info.value.args[0]
        == "columns is not a valid type. Valid types: [tuple, list, dict], Passed: <class 'set'>"
    )


@pytest.mark.parametrize(
    "append_params",
    ["basic", "all_fields"],
    indirect=True,
)
@pytest.mark.parametrize(
    "database_table_fixture",
    [
        {"database": Database.SNOWFLAKE},
        {"database": Database.BIGQUERY},
        {"database": Database.POSTGRES},
        {"database": Database.SQLITE},
        {"database": Database.REDSHIFT},
    ],
    indirect=True,
    ids=["snowflake", "bigquery", "postgresql", "sqlite", "redshift"],
)
@pytest.mark.parametrize(
    "multiple_tables_fixture",
    [
        {
            "items": [
                {
                    "file": File(path=str(CWD) + "/../../data/homes_main.csv"),
                },
                {
                    "file": File(path=str(CWD) + "/../../data/homes_append.csv"),
                },
            ],
        }
    ],
    indirect=True,
)
def test_append(database_table_fixture, sample_dag, multiple_tables_fixture, append_params):
    app_param, validate_append = append_params
    main_table, append_table = multiple_tables_fixture
    with sample_dag:
        appended_table = aql.append(
            **app_param,
            target_table=main_table,
            source_table=append_table,
        )
        validate_append(appended_table)
        aql.cleanup()
    test_utils.run_dag(sample_dag)


@pytest.mark.parametrize(
    "database_table_fixture",
    [{"database": Database.POSTGRES}],
    indirect=True,
    ids=["postgresql"],
)
def test_append_on_tables_on_different_db(sample_dag, database_table_fixture):
    test_table_1 = Table(conn_id="postgres_conn")
    test_table_2 = Table(conn_id="sqlite_conn")
    with pytest.raises(ValueError) as exec_info:
        with sample_dag:
            load_main = aql.load_file(
                input_file=File(path=str(CWD) + "/../../data/homes_main.csv"),
                output_table=test_table_1,
            )
            load_append = aql.load_file(
                input_file=File(path=str(CWD) + "/../../data/homes_append.csv"),
                output_table=test_table_2,
            )
            aql.append(
                target_table=load_main,
                source_table=load_append,
            )
        test_utils.run_dag(sample_dag)
    assert exec_info.value.args[0] == "source and target table must belong to the same datasource"


@pytest.mark.skipif(not DATASET_SUPPORT, reason="Inlets/Outlets will only be added for Airflow >= 2.4")
def test_inlets_outlets_supported_ds():
    """Test Datasets are set as inlets and outlets"""
    input_file = File("gs://bucket/object.csv")
    output_table = Table("test_name")
    task = aql.load_file(
        input_file=input_file,
        output_table=output_table,
    )
    assert task.operator.inlets == [input_file]
    assert task.operator.outlets == [output_table]


@pytest.mark.skipif(DATASET_SUPPORT, reason="Inlets/Outlets will only be added for Airflow >= 2.4")
def test_inlets_outlets_non_supported_ds():
    """Test inlets and outlets are not set if Datasets are not supported"""
    input_file = File("gs://bucket/object.csv")
    output_table = Table("test_name")
    task = aql.load_file(
        input_file=input_file,
        output_table=output_table,
    )
    assert task.operator.inlets == []
    assert task.operator.outlets == []
