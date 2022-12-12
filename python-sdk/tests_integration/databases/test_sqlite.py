import os
import pathlib

import pandas as pd
import pytest
import sqlalchemy
from airflow.hooks.base import BaseHook

from astro.constants import Database
from astro.databases import create_database
from astro.databases.sqlite import SqliteDatabase
from astro.exceptions import NonExistentTableException
from astro.files import File
from astro.table import Table
from astro.utils.load import copy_remote_file_to_local

from ..sql.operators import utils as test_utils

CWD = pathlib.Path(__file__).parent

DEFAULT_CONN_ID = "sqlite_default"
CUSTOM_CONN_ID = "sqlite_conn"
SUPPORTED_CONN_IDS = [DEFAULT_CONN_ID, CUSTOM_CONN_ID]


@pytest.mark.parametrize("conn_id", SUPPORTED_CONN_IDS)
def test_create_database(conn_id):
    """Check that the database is created with the correct class."""
    database = create_database(conn_id)
    assert isinstance(database, SqliteDatabase)


@pytest.mark.parametrize(
    "conn_id,expected_db_path",
    [
        (
            DEFAULT_CONN_ID,
            BaseHook.get_connection(DEFAULT_CONN_ID).host,
        ),  # Linux and MacOS have different hosts
        (CUSTOM_CONN_ID, "/tmp/sqlite.db"),
    ],
    ids=SUPPORTED_CONN_IDS,
)
def test_sqlite_sqlalchemy_engine(conn_id, expected_db_path):
    """Confirm that the SQLAlchemy is created successfully and verify DB path."""
    database = SqliteDatabase(conn_id)
    engine = database.sqlalchemy_engine
    assert isinstance(engine, sqlalchemy.engine.base.Engine)
    assert engine.url.database == expected_db_path


@pytest.mark.integration
def test_sqlite_run_sql_with_sqlalchemy_text():
    """Run a SQL statement using SQLAlchemy text"""
    statement = sqlalchemy.text("SELECT 1 + 1;")
    database = SqliteDatabase()
    response = database.run_sql(statement)
    assert response.first()[0] == 2


@pytest.mark.integration
def test_sqlite_run_sql():
    """Run a SQL statement using plain string."""
    statement = "SELECT 1 + 1;"
    database = SqliteDatabase()
    response = database.run_sql(statement)
    assert response.first()[0] == 2


@pytest.mark.integration
def test_sqlite_run_sql_with_parameters():
    """Test running a SQL query using SQLAlchemy templating engine"""
    statement = "SELECT 1 + :value;"
    database = SqliteDatabase()
    response = database.run_sql(statement, parameters={"value": 1})
    assert response.first()[0] == 2


@pytest.mark.integration
def test_table_exists_raises_exception():
    """Raise an exception when checking for a non-existent table"""
    database = SqliteDatabase()
    assert not database.table_exists(Table(name="inexistent-table"))


@pytest.mark.integration
@pytest.mark.parametrize(
    "database_table_fixture",
    [
        {
            "database": Database.SQLITE,
            "table": Table(
                columns=[
                    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
                    sqlalchemy.Column("name", sqlalchemy.String(60), nullable=False, key="name"),
                ]
            ),
        }
    ],
    indirect=True,
    ids=["sqlite"],
)
def test_sqlite_create_table_with_columns(database_table_fixture):
    """Create a table using specific columns and types"""
    database, table = database_table_fixture

    statement = f"PRAGMA table_info({table.name});"
    response = database.run_sql(statement)
    assert response.first() is None

    database.create_table(table)
    response = database.run_sql(statement)
    rows = response.fetchall()
    assert len(rows) == 2
    assert rows[0] == (0, "id", "INTEGER", 1, None, 1)
    assert rows[1] == (1, "name", "VARCHAR(60)", 1, None, 0)


@pytest.mark.integration
@pytest.mark.parametrize(
    "database_table_fixture",
    [{"database": Database.SQLITE, "table": Table()}],
    indirect=True,
    ids=["sqlite"],
)
def test_sqlite_create_table_autodetection_with_file(database_table_fixture):
    """Create a table using specific columns and types"""
    database, table = database_table_fixture

    statement = f"PRAGMA table_info({table.name});"
    response = database.run_sql(statement)
    assert response.first() is None

    filepath = str(pathlib.Path(CWD.parent, "data/sample.csv"))
    database.create_table(table, File(filepath))
    response = database.run_sql(statement)
    rows = response.fetchall()
    assert len(rows) == 2
    assert rows[0] == (0, "id", "BIGINT", 0, None, 0)
    assert rows[1] == (1, "name", "TEXT", 0, None, 0)


@pytest.mark.integration
@pytest.mark.parametrize(
    "database_table_fixture",
    [{"database": Database.SQLITE, "table": Table()}],
    indirect=True,
    ids=["sqlite"],
)
def test_sqlite_create_table_autodetection_without_file(database_table_fixture):
    """Create a table using specific columns and types"""
    database, table = database_table_fixture

    statement = f"PRAGMA table_info({table.name});"
    response = database.run_sql(statement)
    assert response.first() is None

    with pytest.raises(ValueError) as exc_info:
        database.create_table(table)
    assert exc_info.match("File or Dataframe is required for creating table using schema autodetection")


@pytest.mark.integration
@pytest.mark.parametrize(
    "database_table_fixture",
    [
        {"database": Database.SQLITE},
    ],
    indirect=True,
    ids=["sqlite"],
)
def test_load_pandas_dataframe_to_table(database_table_fixture):
    """Load Pandas Dataframe to a SQL table"""
    database, table = database_table_fixture

    pandas_dataframe = pd.DataFrame(data={"id": [1, 2]})
    database.load_pandas_dataframe_to_table(pandas_dataframe, table)

    statement = f"SELECT * FROM {table.name};"
    response = database.run_sql(statement)

    rows = response.fetchall()
    assert len(rows) == 2
    assert rows[0] == (1,)
    assert rows[1] == (2,)


@pytest.mark.integration
@pytest.mark.parametrize(
    "database_table_fixture",
    [
        {"database": Database.SQLITE},
    ],
    indirect=True,
    ids=["sqlite"],
)
def test_load_file_to_table(database_table_fixture):
    """Load a file to a SQL table"""
    database, target_table = database_table_fixture
    filepath = str(pathlib.Path(CWD.parent, "data/sample.csv"))
    database.load_file_to_table(File(filepath), target_table, {})

    df = database.hook.get_pandas_df(f"SELECT * FROM {target_table.name}")
    assert len(df) == 3
    expected = pd.DataFrame(
        [
            {"id": 1, "name": "First"},
            {"id": 2, "name": "Second"},
            {"id": 3, "name": "Third with unicode पांचाल"},
        ]
    )
    test_utils.assert_dataframes_are_equal(df, expected)


@pytest.mark.integration
@pytest.mark.parametrize(
    "database_table_fixture",
    [
        {
            "database": Database.SQLITE,
            "file": File(str(pathlib.Path(CWD.parent, "data/sample.csv"))),
        }
    ],
    indirect=True,
    ids=["sqlite"],
)
def test_export_table_to_file_overrides_existing_file(database_table_fixture):
    """Override file if using the replace option"""
    database, populated_table = database_table_fixture

    filepath = str(pathlib.Path(CWD.parent, "data/sample.csv").absolute())
    database.export_table_to_file(populated_table, File(filepath), if_exists="replace")

    df = test_utils.load_to_dataframe(filepath, "csv")
    assert len(df) == 3
    expected = pd.DataFrame(
        [
            {"id": 1, "name": "First"},
            {"id": 2, "name": "Second"},
            {"id": 3, "name": "Third with unicode पांचाल"},
        ]
    )
    assert df.rename(columns=str.lower).equals(expected)


@pytest.mark.integration
@pytest.mark.parametrize(
    "database_table_fixture",
    [{"database": Database.SQLITE}],
    indirect=True,
    ids=["sqlite"],
)
def test_export_table_to_pandas_dataframe_non_existent_table_raises_exception(
    database_table_fixture,
):
    """Export table to a Pandas dataframe"""
    database, non_existent_table = database_table_fixture

    with pytest.raises(NonExistentTableException) as exc_info:
        database.export_table_to_pandas_dataframe(non_existent_table)
    error_message = exc_info.value.args[0]
    assert error_message.startswith("The table")
    assert error_message.endswith("does not exist")


@pytest.mark.integration
@pytest.mark.parametrize(
    "database_table_fixture",
    [
        {
            "database": Database.SQLITE,
            "file": File(str(pathlib.Path(CWD.parent, "data/sample.csv"))),
        }
    ],
    indirect=True,
    ids=["sqlite"],
)
@pytest.mark.parametrize(
    "remote_files_fixture",
    [{"provider": "google", "file_create": False}],
    indirect=True,
    ids=["google"],
)
def test_export_table_to_file_in_the_cloud(database_table_fixture, remote_files_fixture):
    """Export a SQL tale to a file in the cloud"""
    object_path = remote_files_fixture[0]
    database, populated_table = database_table_fixture

    database.export_table_to_file(
        populated_table,
        File(object_path),
        if_exists="replace",
    )

    filepath = copy_remote_file_to_local(object_path)
    df = pd.read_csv(filepath)
    assert len(df) == 3
    expected = pd.DataFrame(
        [
            {"id": 1, "name": "First"},
            {"id": 2, "name": "Second"},
            {"id": 3, "name": "Third with unicode पांचाल"},
        ]
    )
    test_utils.assert_dataframes_are_equal(df, expected)
    os.remove(filepath)


@pytest.mark.integration
@pytest.mark.parametrize(
    "database_table_fixture",
    [
        {
            "database": Database.SQLITE,
            "file": File(str(pathlib.Path(CWD.parent, "data/sample.csv"))),
        }
    ],
    indirect=True,
    ids=["sqlite"],
)
def test_create_table_from_select_statement(database_table_fixture):
    """Create a table given a SQL select statement"""
    database, original_table = database_table_fixture

    statement = f"SELECT * FROM {database.get_table_qualified_name(original_table)} WHERE id = 1;"
    target_table = Table()
    database.create_table_from_select_statement(statement, target_table)

    df = database.hook.get_pandas_df(f"SELECT * FROM {target_table.name}")
    assert len(df) == 1
    expected = pd.DataFrame([{"id": 1, "name": "First"}])
    test_utils.assert_dataframes_are_equal(df, expected)
    database.drop_table(target_table)
