.. _load_file:

============================================================
:py:mod:`load_file operator <astro.sql.operators.load_file>`
============================================================

When to use the ``load_file`` operator
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The ``load_file`` operator allows you to load data from files into your target transformation system.

There are two uses of the ``load_file`` operator.

#. Loading a file(s) into a database table
#. Loading a file(s) into a Pandas dataframe

Case 1: Load files into a database table
    To load files into a database table, you need to provide the name and connection to the target table with the ``output_table`` parameter. The operator will return an instance of the table object passed in ``output_table``. If the specified table does not already exist, it will be created. If it does already exist, it will be replaced, unless the `if_exists` parameter is modified.

    .. literalinclude:: ../../../../example_dags/example_load_file.py
       :language: python
       :start-after: [START load_file_example_1]
       :end-before: [END load_file_example_1]

Case 2: Load files into a Pandas dataframe
    If you don't provide an ``output_table`` to the ``load_file`` operator, it will convert the file into a Pandas dataframe and return the reference to dataframe.

    .. literalinclude:: ../../../../example_dags/example_load_file.py
       :language: python
       :start-after: [START load_file_example_2]
       :end-before: [END load_file_example_2]

.. _custom_schema:

Parameters to use when loading a file to a database table
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. **if_exists** - If the table you trying to create already exists, you can specify whether you want to replace the table or append the new data by specifying either ``if_exists='append'`` or ``if_exists='replace'``.

    .. literalinclude:: ../../../../example_dags/example_load_file.py
       :language: python
       :start-after: [START load_file_example_4]
       :end-before: [END load_file_example_4]

    Note that if you use ``if_exists='replace'``, the existing table will be dropped and the schema of the new data will be used.

#. **output_table** - This parameter defines the output table to load data to, which should be an instance of ``astro.sql.table.Table``. You can specify the schema of the table by providing a list of the instance of ``sqlalchemy.Column <https://docs.sqlalchemy.org/en/14/core/metadata.html#sqlalchemy.schema.Column>`` to the ``columns`` parameter. If you don't specify a schema, it will be inferred using Pandas.

    .. literalinclude:: ../../../../example_dags/example_load_file.py
       :language: python
       :start-after: [START load_file_example_5]
       :end-before: [END load_file_example_5]

#. **columns_names_capitalization** - If you are working with a ``Snowflake`` database with :ref:`table_schema` and with ``if_exists=replace``, you can control whether the column names of the output table are capitalized. The default is to convert all column names to lowercase. Valid inputs are ``lower``, ``upper``, or ``original`` which will convert column names to lowercase.

#. **ndjson_normalize_sep** - If your input file type is NDJSON, you can use this parameter to normalize the data to two dimensions. This makes the data suitable for loading into a table. This parameter is used as a delimiter for combining columns names if required.

    example:
        input JSON:

        .. code:: python

           {"a": {"b": "c"}}

        output table:

        .. list-table::
           :widths: auto

           * - a_b
           * - c

    Note - columns a and b are merged to form one column a_b and `_` is used as a delimiter.

    .. literalinclude:: ../../../../example_dags/example_load_file.py
       :language: python
       :start-after: [START load_file_example_3]
       :end-before: [END load_file_example_3]

.. _table_schema:

Inferring a Table Schema
~~~~~~~~~~~~~~~~~~~~~~~~

There are three ways to infer the schema of the table to be created, listed by priority:

#. **User specified schema** - You can specify the schema of the table to be created in the Table object, like the ``output_table`` section in :ref:`custom_schema`

#. **Native auto schema detection** - If available, this will be used over pandas auto schema detection below, which will use the schema inference mechanism provided by the database.

#. **Pandas auto schema detection** - if you don't specify the schema in the table object, then ``load_file`` will infer the schema using the top 1000 rows. The default value of rows to look at is 1000, but this can be changed by creating an environment variable.

    .. code-block:: shell

       AIRFLOW__ASTRO_SDK_LOAD_TABLE_AUTODETECT_ROWS_COUNT

    Or within your Airflow config:

    .. code-block:: ini

       [astro_sdk]
       load_table_autodetect_rows_count = 1000

    Note - this only applies to :ref:`filetype` JSON, NDJSON and CSV. PARQUET files have type information so schema inference is unnecessary.


Parameters to use when loading a file to a Pandas dataframe
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#. **columns_names_capitalization**: Use to control the capitalization of column names in the generated dataframe. The default value is ``original``.

        *  **original** - Remains the same as the input file
        *  **upper** - Convert to uppercase
        *  **lower** - Convert to lowercase

    .. literalinclude:: ../../../../example_dags/example_load_file.py
       :language: python
       :start-after: [START load_file_example_6]
       :end-before: [END load_file_example_6]


Parameters for native transfer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Refer to :ref:`load_file_working` for details on Native Path.

#. **use_native_support**: Native transfer support is available for some file sources and databases. If it is available for your systems, the default is to use this support. To leverage native transfer support, certain settings may need to be modified on your destination database. If you do not wish to use native transfer support, you can turn off this behavior by specifying ``use_native_support=False``.

        This feature is enabled by default, to disable it refer to the example below.

        .. literalinclude:: ../../../../example_dags/example_load_file.py
           :language: python
           :start-after: [START load_file_example_7]
           :end-before: [END load_file_example_7]

        To check if the native transfer will be used for your combination of file location and database, refer to :ref:`supported_native_path`.

        **When to turn off native transfer:**

            * Sometimes additional services need to be enabled on the target database to use native transfer.

               For example, see  https://cloud.google.com/bigquery-transfer/docs/s3-transfer

            * There may be additional costs associated due to the services used to perform the native transfer.

            * Native transfers are overkill in cases when you are transferring smaller files. It may take less time to load small files using the default approach.

#. **native_support_kwargs**: ``load_file`` supports multiple databases that may require different parameters like to process a file or control error rate. You can specify those parameters in ``native_support_kwargs``. These parameters will be passed to the destination database.

        Check for valid parameters based on **file location** and **database** combination in :ref:`supported_native_path`

        .. literalinclude:: ../../../../example_dags/example_load_file.py
           :language: python
           :start-after: [START load_file_example_8]
           :end-before: [END load_file_example_8]


#. **enable_native_fallback**: When ``use_native_support`` is set to ``True``, ``load_file`` will attempt to use native transfer. If this fails, ``load_file`` task will fail unless you :ref:`configure_native_fallback`

        .. literalinclude:: ../../../../example_dags/example_load_file.py
           :language: python
           :start-after: [START load_file_example_9]
           :end-before: [END load_file_example_9]

.. _supported_native_path:

Supported native transfers
~~~~~~~~~~~~~~~~~~~~~~~~~~
.. list-table::
   :widths: auto

   * - File Location
     - Database
     - native_support_kwargs params
     - Permission
   * - S3
     - Bigquery
     - https://cloud.google.com/bigquery-transfer/docs/s3-transfer#bq
     - https://cloud.google.com/bigquery/docs/s3-transfer#required_permissions and ``bigquery.jobs.create``
   * - GCS
     - Bigquery
     - https://cloud.google.com/bigquery-transfer/docs/cloud-storage-transfer#bq
     - https://cloud.google.com/bigquery/docs/cloud-storage-transfer#required_permissions and ``bigquery.jobs.create``
   * - S3
     - Snowflake
     - https://docs.snowflake.com/en/sql-reference/sql/copy-into-table.html
     - https://docs.snowflake.com/en/user-guide/data-load-s3.html
   * - GCS
     - Snowflake
     - https://docs.snowflake.com/en/sql-reference/sql/copy-into-table.html
     - https://docs.snowflake.com/en/user-guide/data-load-gcs-config.html
   * - S3
     - Redshift
     - https://docs.aws.amazon.com/redshift/latest/dg/r_COPY.html
     - https://docs.aws.amazon.com/redshift/latest/dg/c-getting-started-using-spectrum-create-role.html

.. note::
   For loading from S3 to Redshift database, although Redshift allows the below two options for authorization, **we
   only support the IAM Role option** as if you pass CREDENTIALS in the query, they might get printed in logs and
   have a potential risk of getting leaked:

   1. IAM Role
   2. CREDENTIALS

   Reference on how to create such a role is here: https://www.dataliftoff.com/iam-roles-for-loading-data-from-s3-into-redshift/

Patterns in file path
~~~~~~~~~~~~~~~~~~~~~

``load_file`` can resolve patterns in file path. There are three types of patterns supported based on the :ref:`file_location`

#. **Local** - On local we support glob pattern - `glob doc <https://docs.python.org/3/library/glob.html>`_

    .. literalinclude:: ../../../../example_dags/example_load_file.py
       :language: python
       :start-after: [START load_file_example_10]
       :end-before: [END load_file_example_10]

#. **S3** - prefix in file path - `S3 doc <https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-prefixes.html>`_

    .. literalinclude:: ../../../../example_dags/example_load_file.py
       :language: python
       :start-after: [START load_file_example_11]
       :end-before: [END load_file_example_11]

#. **GCS** - prefix in file path - `GCS doc <https://cloud.google.com/storage/docs/listing-objects>`_

    .. literalinclude:: ../../../../example_dags/example_load_file.py
       :language: python
       :start-after: [START load_file_example_12]
       :end-before: [END load_file_example_12]

#. **GCS to Bigquery** - only applicable when using native path(for details check -:ref:`load_file_working`)

    When loading data from ``GCS`` to ``Bigquery``, we by default use the native path, which is faster since the schema detection and pattern are processed directly by ``Bigquery``. We can also process multiple files by passing a pattern; for a valid pattern, check `Bigquery doc <https://cloud.google.com/bigquery/docs/reference/rest/v2/Job#jobconfigurationload>`_ and look for the ``sourceUris`` field.


Inferring file type
~~~~~~~~~~~~~~~~~~~

:ref:`filetype` will be inferred in two ways with the following priority:

#. **File object** - If the user has passed the ``filetype`` parameter while declaring the ``astro.files.File`` object, that file type will be used. Valid values are listed in :ref:`filetype`.

    .. literalinclude:: ../../../../example_dags/example_load_file.py
       :language: python
       :start-after: [START load_file_example_10]
       :end-before: [END load_file_example_10]

    Note - This parameter becomes mandatory when the file path don't have an extension.

#. **From file extensions** - When an ``astro.files.File`` object is created and provided a fully qualified path, the file extension is used to infer file type. Here the file type is CSV.

    .. literalinclude:: ../../../../example_dags/example_load_file.py
       :language: python
       :start-after: [START load_file_example_4]
       :end-before: [END load_file_example_4]


Loading data from HTTP API
~~~~~~~~~~~~~~~~~~~~~~~~~~
Users can also load data from an HTTP API:

.. literalinclude:: ../../../../example_dags/example_google_bigquery_gcs_load_and_save.py
   :language: python
   :start-after: [START load_file_http_example]
   :end-before: [END load_file_http_example]


Default Datasets
~~~~~~~~~~~~~~~~
If you are using the Astro Python SDK version 1.1 or later, you do not need to make any code
updates to use  `Datasets <https://github.com/astronomer/astro-sdk/blob/main/python-sdk/docs/concepts.rst#datasets>`_

Datasets are automatically registered for any
functions with output tables in Astro Python SDK version 1.1 or later,
and you do not need to define any ``outlets`` parameter.

Note that a default Dataset URI generated by Astro Python SDK will be in the format
``astro://test_conn@?table=test_table&schema=schema&database=database``

For ``load_file`` operator,

* Input Dataset - Source file for the operator.
* Output Dataset - Target table of the operator.

These Datasets can be used by Airflow 2.4 and above to show data dependencies between DAGs.


Snowflake Identifier
~~~~~~~~~~~~~~~~~~~~

Table
=====
We are creating tables in uppercase. This has an impact when we run raw SQL queries. For example, if we create a table with the name ``customer`` or ``Customer`` or ``CUSTOMER``, in the query we have to use the uppercase or lowercase name ``CUSTOMER`` or ``customer`` without quotes. Example ``Select * from CUSTOMER`` or ``Select * from customer``.


Columns
=======

When loading data to the snowflake table from a file there are three cases concerning column names

* Uppercase: When all your column names are in uppercase
* Lowercase: When all your column names are in uppercase
* Mixed case: When your column names are like - ``List`` etc.

Mixed
-----
* Run raw SQL

    .. warning::
        When we load data we are preserving the case by adding quotes to column names. We need to be aware of this behavior while running raw SQL queries.
        With mixed columns, you will have to add quotes for all the column names. Like ``select "Name" from customer``.

        Example -
        if we try to load a below mentioned CSV File with load_file():

        .. list-table::
           :widths: auto

           * - Name
             - Age
           * - John
             - 20
           * - Sam
             - 30

        When we run a SQL query we have to preserve the casing by passing the identifier in quotes. For example - ``SELECT "Name", "Age" FROM <table_name>``

* Dataframes

    There is no impact when we try to convert the table into a dataframe.

Upper/Lower
-----------
* Run raw SQL

    For upper or lowercase we don't have an impact, we can simply run queries without adding quotes around column names.

* Dataframe

    .. warning::
       We will have lowercase col names even for uppercase names in the file. For example, if you have below mentioned file, which we load via ``load_file()`` operator.

       .. list-table::
          :widths: auto

          * - NAME
            - AGE
          * - John
            - 20
          * - Sam
            - 30

       When we load this into a dataframe, you will get columns in lowercase - ``name`` and ``age``
