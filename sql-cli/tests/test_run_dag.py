from __future__ import annotations

import pathlib
import sqlite3
from unittest import mock

import airflow
import pytest
from airflow.decorators import task
from airflow.utils.cli import get_dag
from airflow.utils.trigger_rule import TriggerRule
from packaging.version import Version
from sqlalchemy.exc import OperationalError

from astro import sql as aql
from sql_cli.exceptions import ConnectionFailed
from sql_cli.run_dag import _run_task, run_dag
from sql_cli.utils.airflow import initialise as initialise_airflow, reload as reload_airflow

CWD = pathlib.Path(__file__).parent


@pytest.fixture(scope="module")
def airflow_home(tmp_path_factory):
    return tmp_path_factory.mktemp("airflow")


@pytest.fixture(autouse=True, scope="module")
def airflow_setup(airflow_home):
    # Set up the database
    initialise_airflow(airflow_home, airflow_home / "dags")
    # Reload airflow to be able to use reloaded airflow modules
    reload_airflow(airflow_home)


def airflow_less_than(threshold: Version) -> bool:
    """
    Check if Airflow is less than a given threshold version.

    :param threshold: version tuple (e.g. (2, 3)).
    """
    current_version = Version(airflow.__version__)
    return current_version < threshold


@mock.patch("airflow.models.taskinstance.TaskInstance")
@mock.patch("airflow.settings.SASession")
def test_run_task_successfully(mock_session, mock_task_instance, capsys):
    mock_task_instance.map_index = 0
    _run_task(mock_task_instance, mock_session)
    mock_task_instance._run_raw_task.assert_called_once()
    mock_session.flush.assert_called_once()
    captured = capsys.readouterr()
    assert "SUCCESS" in captured.out


@pytest.mark.parametrize(
    "side_effect,exception",
    [
        (
            OperationalError(
                statement=mock.ANY,
                params=mock.ANY,
                orig=sqlite3.OperationalError("no such table: orders"),
            ),
            ConnectionFailed,
        ),
    ],
)
@mock.patch("airflow.models.taskinstance.TaskInstance")
@mock.patch("airflow.settings.SASession")
def test_run_task_failed(mock_session, mock_task_instance, capsys, side_effect, exception):
    mock_task_instance.task.conn_id = "sqlite_conn"
    mock_task_instance._run_raw_task.side_effect = side_effect
    mock_task_instance.map_index = 0
    with pytest.raises(exception):
        _run_task(mock_task_instance, mock_session)
    mock_task_instance._run_raw_task.assert_called_once()
    mock_session.flush.assert_not_called()
    captured = capsys.readouterr()
    assert "FAILED" in captured.out


def test_run_task_cleanup_log(sample_dag, capsys):
    @aql.dataframe
    def upstream_task():
        return 5

    @aql.dataframe
    def downstream_task(f):
        return f

    with sample_dag:
        downstream_task(upstream_task())
        aql.cleanup()
    run_dag(sample_dag)
    captured = capsys.readouterr()
    assert "aql.cleanup async, continuing" in captured.out


@pytest.mark.skipif(airflow_less_than(Version("2.3")), reason="Dynamic tasks were introduced in Airflow 2.3")
def test_run_dag_dynamic_task(sample_dag, capsys):
    @task
    def get_list():
        return [1, 2, 3]

    @task
    def print_val(v):
        print(v)

    with sample_dag:
        print_val.expand(v=get_list())
    run_dag(sample_dag)
    captured = capsys.readouterr()
    for i in [1, 2]:
        assert f"Processing print_val[{i}]..." in captured.out


@pytest.mark.skipif(airflow_less_than(Version("2.3")), reason="Dynamic tasks were introduced in Airflow 2.3")
def test_run_dag_with_skip(sample_dag, capsys):
    @task.branch
    def who_is_prettiest():
        return "snow_white_wins"

    @task
    def snow_white_wins():
        return "the witch is mad"

    @task
    def witch_wins():
        return "the witch is happy"

    @task(trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS)
    def movie_ends():
        return "movie ends"

    with sample_dag:
        who_is_prettiest() >> [snow_white_wins(), witch_wins()] >> movie_ends()  # skipcq: PYL-W0106
    run_dag(sample_dag)
    captured = capsys.readouterr()
    assert "Processing witch_wins... SUCCESS" not in captured.out
    assert "Processing snow_white_wins... SUCCESS" in captured.out
    assert "Processing movie_ends... SUCCESS" in captured.out


def test_run_dag(capsys, caplog):
    dag = get_dag(dag_id="example_dataframe", subdir=f"{CWD}/test_dag")
    run_dag(dag)
    captured = capsys.readouterr()
    assert "The worst month was" in captured.out
    assert not any(record.name == "airflow.task" for record in caplog.records)


def test_run_dag_verbose(capsys):
    dag = get_dag(dag_id="example_dataframe", subdir=f"{CWD}/test_dag")
    run_dag(dag, verbose=True)
    captured = capsys.readouterr()
    assert "The worst month was" in captured.out


def test_run_dag_with_conn_id(capsys):
    dag = get_dag(dag_id="example_sqlite_load_transform", subdir=f"{CWD}/test_dag")
    run_dag(dag, conn_file_path=f"{CWD}/test_conn.yaml")
    captured = capsys.readouterr()
    assert "top movie:" in captured.out
