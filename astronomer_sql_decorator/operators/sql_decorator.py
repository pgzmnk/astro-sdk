from builtins import NotImplementedError
import os
from typing import Dict

from psycopg2.extensions import AsIs
import pandas as pd
import pandas.io.sql as sqlio

from airflow.decorators.base import DecoratedOperator
from airflow.models import TaskInstance, DagRun
from airflow.utils.db import check, provide_session
from airflow.models.xcom import BaseXCom
from airflow.providers.postgres.hooks.postgres import PostgresHook


class SqlDecoratoratedOperator(DecoratedOperator):
    def __init__(self,
                 to_dataframe=False,
                 to_temp_table=False,
                 cache=False,
                 from_s3=False,
                 from_csv='False',
                 **kwargs):
        self.to_dataframe = to_dataframe
        self.to_temp_table = to_temp_table
        self.input_table = None
        self.cache = cache
        self.from_s3 = from_s3
        self.from_csv = from_csv
        self.kwargs = kwargs
        self.op_kwargs = self.kwargs.get('op_kwargs')

        if kwargs["op_kwargs"].get("input_table"):
            self.input_table = kwargs["op_kwargs"].pop("input_table")
            if to_dataframe:
                kwargs["op_kwargs"]["input_df"] = None

        super().__init__(
            **kwargs,
        )

    def execute(self, context: Dict):
        input_table = self.handle_input_table()

        if self.from_s3:
            # Load from s3
            self._s3_to_db(
                s3_path=self.op_kwargs.get('s3_path'),
                conn=self.kwargs['postgres_conn_id'],
                table_name=self.input_table)

        elif self.from_csv:
            # Load from csv
            self._csv_to_db(
                csv_path=self.op_kwargs.get('csv_path'),
                conn=self.kwargs['postgres_conn_id'],
                table_name=self.input_table)

        if self.to_dataframe:
            return self.handle_dataframe_func(input_table=input_table)
        else:
            # To-do: pass parameters

            # To-do: ADDRESS ERROR: `task_from_local_csv() got an unexpected keyword argument 's3_path'`
            # @dimberman
            sql_stuff = self.python_callable(
                input_table=self.input_table,
                s3_path=None)

        # To-do: Type check `sql_stuff`

        # If we return two things, assume the second thing is the params
        if len(sql_stuff) == 2:
            self.sql, self.parameters = sql_stuff
        else:
            self.sql = sql_stuff
            self.parameters = {}

        # Create a table name for the temp table
        # To-do: if `output_table` defined, name it `output_table`
        ouput_table_name = self.kwargs.get('op_kwargs').get(
            'output_table') or self.create_table_name(context)

        self.sql = self.create_temporary_table(self.sql, ouput_table_name)

        # Automatically add any kwargs going into the function
        if self.op_kwargs:
            self.parameters.update(self.op_kwargs)

        # While normally it is a security anti-pattern to use AsIs in SQL, this value is never user controlled
        # The only way a user could modify this value is if they already own the metadata DB, which would be a much
        # deeper security breach.
        self.parameters['input_table'] = AsIs(input_table)
        self.parameters = {k: AsIs(v) for k, v in self.parameters.items()}

        # Run execute function of subclassed Operator.
        super().execute(context)

        if self.to_temp_table:
            return ouput_table_name

    @staticmethod
    def create_temporary_table(query, table_name):
        """
        Create a temp table for the current task instance. This table will be overwritten if the DAG is run again as this
        table is only ever meant to be temporary.
        :param query:
        :param table_name:
        :return:
        """
        return f"DROP TABLE IF EXISTS {table_name}; CREATE TABLE {table_name} AS ({query});"

    @staticmethod
    def create_cte(query, table_name):
        return f"WITH {table_name} AS ({query}) SELECT * FROM {table_name};"

    @staticmethod
    def create_table_name(context):
        ti: TaskInstance = context['ti']
        dag_run: DagRun = ti.get_dagrun()
        return f"{dag_run.dag_id}_{ti.task_id}_{int(ti.execution_date.timestamp())}"

    def handle_input_table(self):
        """
        For security reasons, we don't want the user having actual control over the input_table variable.
        This is because there is no sql injection safe way that we can allow user input for this variable.
        This function pulls the input table out of the arguments
        :return:
        """
        if not self.input_table:
            if self.op_kwargs.get('input_table'):
                input_table = self.op_kwargs.pop('input_table')
            else:
                op_args_list = list(self.op_args)
                input_table = op_args_list.pop(0)
                self.op_args = tuple(op_args_list)
        else:
            input_table = self.input_table
        return input_table

    def handle_dataframe_func(self, input_table):
        raise NotImplementedError("Need to add dataframe func to class")

    @provide_session
    def pre_execute(self, context, session=None):
        """This hook is triggered right before self.execute() is called.
        """
        pass

    def post_execute(self, context, result=None):
        """
        This hook is triggered right after self.execute() is called.
        """
        pass

    def _table_exists_in_db(self, conn: str, table_name: str):
        """Override this method to enable sensing db.
        """
        raise NotImplementedError("Add _table_exists_in_db method to class")

    def _transfer_to_s3(self, conn: str, table_name: str):
        """Override this method to enable write to S3.
        """
        raise NotImplementedError("Add _transfer_to_s3 method to class")

    def _transfer_from_s3(self, conn: str, table_name: str):
        """Override this method to enable read from to S3.
        """
        raise NotImplementedError("Add _transfer_from_s3 method to class")

    def _s3fs_creds(self):
        """Structure s3fs credentials from Airflow connection.

        s3fs enables pandas to write to s3
        """
        # To-do: clean-up how S3 creds are passed to s3fs
        k, v = os.environ['AIRFLOW_CONN_AWS_DEFAULT'].replace(
            '%2F', '/').replace('aws://', '').replace('@', '').split(':')

        return {'key': k, 'secret': v}

    def _cleanup(self):
        """Remove DAG's objects from S3 and db.
        """
        # To-do
        pass

    def _s3_to_db(self, s3_path: str, conn: str, table_name: str):
        """Override this method to enable transfer from S3 to selected database.
        """
        raise NotImplementedError("Add _s3_to_db method to class")

    def _s3_to_db(self, s3_path: str, conn: str, table_name: str):
        """Override this method to enable transfer from csv to selected database.
        """
        raise NotImplementedError("Add _csv_to_db method to class")
