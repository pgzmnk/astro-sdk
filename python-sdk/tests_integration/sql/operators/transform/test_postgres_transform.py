import pandas as pd
import pytest
from airflow.models import DAG, DagRun, TaskInstance as TI
from airflow.utils import timezone
from airflow.utils.session import create_session

import astro.sql as aql
from astro.constants import Database
from astro.table import Metadata, Table
from tests.sql.operators import utils as test_utils

DEFAULT_DATE = timezone.datetime(2016, 1, 1)


@pytest.fixture
def dag():
    return DAG("test_dag", start_date=DEFAULT_DATE)


@pytest.fixture(autouse=True)
def cleanup():
    yield
    with create_session() as session:
        session.query(DagRun).delete()
        session.query(TI).delete()


@aql.dataframe
def validate(df: pd.DataFrame):
    assert len(df) == 12
    assert df.iloc[0].to_dict()["first_name"] == "PENELOPE"


@pytest.mark.parametrize(
    "output_table",
    [Table(), Table(name="my_table"), Table(name="my_table", conn_id="postgres_conn_pagila")],
)
def test_postgres_to_dataframe_partial_output(output_table, dag):
    @aql.transform
    def sample_pg(input_table: Table):
        return "SELECT * FROM {{input_table}} WHERE last_name LIKE 'G%%'"

    with dag:
        pg_output = sample_pg(
            input_table=Table(
                name="actor",
                conn_id="postgres_conn_pagila",
                metadata=Metadata(schema="public"),
            ),
            output_table=output_table,
        )
        validate(df=pg_output)
    test_utils.run_dag(dag)


@pytest.mark.xfail
def test_with_invalid_dag_name(sample_dag):
    """
    TODO: There appears to be a bug when passing an "invalid" DAG name to pandas when creating a dataframe
    This issue can be tracked here:
    https://app.zenhub.com/workspaces/astro-61e7a085a496df00172965bd/issues/astronomer/astro-sdk/212
    """
    sample_dag.dag_id = "my=dag"

    @aql.transform()
    def pg_query(input_table: Table):
        return "SELECT * FROM {{input_table}} WHERE last_name LIKE 'G%%'"

    with sample_dag:
        pg_table = pg_query(
            input_table=Table(
                name="actor",
                conn_id="postgres_conn_pagila",
                metadata=Metadata(schema="public"),
            )
        )
        validate(pg_table)
    test_utils.run_dag(sample_dag)


@pytest.fixture
def pg_query_result(request):
    query_name = request.param
    if query_name == "basic":
        return "SELECT * FROM {{input_table}} WHERE last_name LIKE 'G%%'"
    if query_name == "semicolon":
        return "SELECT * FROM {{input_table}} WHERE last_name LIKE 'G%%';   "
    if query_name == "with_param":
        return "SELECT * FROM {{input_table}} WHERE last_name LIKE {{last_name}}", {"last_name": "G%%"}
    if query_name == "with_jinja":
        return (
            "SELECT * FROM {{input_table}} WHERE last_update < '{{execution_date}}' AND last_name LIKE 'G%%'"
        )
    if query_name == "with_jinja_template_params":
        return (
            "SELECT * FROM {{input_table}} WHERE last_update < {{r_date}} AND last_name LIKE 'G%%'",
            {"r_date": "{{ execution_date }}"},
        )


@pytest.mark.parametrize(
    "pg_query_result",
    ["basic", "semicolon", "with_param", "with_jinja", "with_jinja_template_params"],
    indirect=True,
)
def test_postgres(sample_dag, pg_query_result):
    @aql.transform
    def pg_query(input_table: Table):
        return pg_query_result

    with sample_dag:
        pg_table = pg_query(
            input_table=Table(
                name="actor",
                conn_id="postgres_conn_pagila",
                metadata=Metadata(schema="public"),
            )
        )
        validate(pg_table)
    test_utils.run_dag(sample_dag)


@pytest.mark.parametrize(
    "database_table_fixture",
    [
        {"database": Database.POSTGRES},
    ],
    indirect=True,
    ids=["postgresql"],
)
def test_postgres_join(sample_dag, database_table_fixture):
    _, test_table = database_table_fixture

    @aql.transform(conn_id="postgres_conn_pagila")
    def sample_pg(actor: Table, film_actor_join: Table, unsafe_parameter):
        return (
            "SELECT {{actor}}.actor_id, first_name, last_name, COUNT(film_id) "
            "FROM {{actor}} JOIN {{film_actor_join}} ON {{actor}}.actor_id = {{film_actor_join}}.actor_id "
            "WHERE last_name LIKE {{unsafe_parameter}} GROUP BY {{actor}}.actor_id"
        )

    @aql.dataframe
    def validate(df: pd.DataFrame):
        assert df.iloc[0].to_dict() == {
            "actor_id": 191,
            "first_name": "GREGORY",
            "last_name": "GOODING",
            "count": 30,
        }

    with sample_dag:
        ret = sample_pg(
            actor=Table(name="actor", conn_id="postgres_conn_pagila", metadata=Metadata()),
            film_actor_join=Table(name="film_actor", metadata=Metadata(schema="public")),
            unsafe_parameter="G%%",
            output_table=test_table,
        )
        validate(ret)


def test_postgres_set_op_kwargs(sample_dag):
    @aql.dataframe
    def validate_result(df: pd.DataFrame):
        assert df.iloc[0].to_dict()["first_name"] == "PENELOPE"

    @aql.transform
    def sample_pg():
        return "SELECT * FROM actor WHERE last_name LIKE 'G%%'"

    with sample_dag:
        pg_df = sample_pg(conn_id="postgres_conn_pagila")
        validate_result(pg_df)
    test_utils.run_dag(sample_dag)
