import pathlib

import pytest
from pandas import DataFrame

from astro.constants import FileType
from astro.databases import create_database
from astro.databases.base import BaseDatabase
from astro.files import File
from astro.table import BaseTable, Table

CWD = pathlib.Path(__file__).parent


class DatabaseSubclass(BaseDatabase):
    pass


def test_openlineage_database_dataset_namespace():
    """
    Test the open lineage dataset namespace for base class
    """
    db = DatabaseSubclass(conn_id="fake_conn_id")
    with pytest.raises(NotImplementedError):
        db.openlineage_dataset_namespace()


def test_openlineage_database_dataset_name():
    """
    Test the open lineage dataset names for the base class
    """
    db = DatabaseSubclass(conn_id="fake_conn_id")
    with pytest.raises(NotImplementedError):
        db.openlineage_dataset_name(table=BaseTable)


def test_subclass_missing_not_implemented_methods_raise_exception():
    db = DatabaseSubclass(conn_id="fake_conn_id")
    with pytest.raises(NotImplementedError):
        db.hook

    with pytest.raises(NotImplementedError):
        db.sqlalchemy_engine

    with pytest.raises(NotImplementedError):
        db.connection

    with pytest.raises(NotImplementedError):
        db.default_metadata

    with pytest.raises(NotImplementedError):
        db.run_sql("SELECT * FROM inexistent_table")


def test_create_table_using_native_schema_autodetection_not_implemented():
    db = DatabaseSubclass(conn_id="fake_conn_id")
    with pytest.raises(NotImplementedError):
        db.create_table_using_native_schema_autodetection(table=Table(), file=File(path="s3://bucket/key"))


def test_subclass_missing_load_pandas_dataframe_to_table_raises_exception():
    db = DatabaseSubclass(conn_id="fake_conn_id")
    table = Table()
    df = DataFrame(data={"col1": [1, 2], "col2": [3, 4]})
    with pytest.raises(NotImplementedError):
        db.load_pandas_dataframe_to_table(df, table)


def test_create_table_using_columns_raises_exception():
    db = DatabaseSubclass(conn_id="fake_conn_id")
    table = Table()
    with pytest.raises(ValueError) as exc_info:
        db.create_table_using_columns(table)
    assert exc_info.match("To use this method, table.columns must be defined")


def test_check_schema_autodetection_is_supported():
    """
    Test the condition native schema autodetection for files and prefixes
    """
    db = create_database("google_cloud_default")
    assert db.check_schema_autodetection_is_supported(
        source_file=File(path="gs://bucket/prefix", filetype=FileType.CSV)
    )

    assert db.check_schema_autodetection_is_supported(source_file=File(path="gs://bucket/prefix/key.csv"))

    assert not (
        db.check_schema_autodetection_is_supported(source_file=File(path="s3://bucket/prefix/key.csv"))
    )


def test_subclass_missing_append_table_raises_exception():
    db = DatabaseSubclass(conn_id="fake_conn_id")
    source_table = Table()
    target_table = Table()
    with pytest.raises(NotImplementedError):
        db.append_table(source_table, target_table, source_to_target_columns_map={})
