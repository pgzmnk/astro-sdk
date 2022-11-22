from pathlib import Path

import pytest
from conftest import DEFAULT_DATE

from sql_cli.dag_generator import Workflow, generate_dag
from sql_cli.exceptions import DagCycle, EmptyDag, WorkflowFilesDirectoryNotFound


def test_workflow(workflow, workflow_with_parameters, sql_file, sql_file_with_parameters):
    """Test that a simple build will return the sql files."""
    assert workflow.sorted_workflow_files() == [sql_file]
    assert workflow_with_parameters.sorted_workflow_files() == [sql_file_with_parameters]


def test_workflow_with_cycle(workflow_with_cycle):
    """Test that an exception is being raised when it is not a DAG."""
    with pytest.raises(DagCycle):
        assert workflow_with_cycle.sorted_workflow_files()


def test_workflow_without_workflow_files():
    """Test that an exception is being raised when it does not have any workflow files."""
    with pytest.raises(EmptyDag):
        Workflow(dag_id="workflow_without_workflow_files", start_date=DEFAULT_DATE, workflow_files=[])


@pytest.mark.parametrize("generate_tasks", [True, False])
def test_generate_dag(root_directory, dags_directory, generate_tasks):
    """Test that the whole DAG generation process including sql files parsing works."""
    dag_file = generate_dag(
        directory=root_directory, dags_directory=dags_directory, generate_tasks=generate_tasks
    )
    assert dag_file


@pytest.mark.parametrize("generate_tasks", [True, False])
def test_generate_dag_invalid_directory(root_directory, dags_directory, generate_tasks):
    """Test that an exception is being raised when the directory does not exist."""
    with pytest.raises(WorkflowFilesDirectoryNotFound):
        generate_dag(directory=Path("foo"), dags_directory=dags_directory, generate_tasks=generate_tasks)
