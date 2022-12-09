from __future__ import annotations

from datetime import datetime

from airflow import DAG

from astro import sql as aql
from astro.files import File
from astro.table import Table


@aql.transform()
def top_five_animations(input_table: Table):
    return """
        SELECT title, rating
        FROM {{input_table}}
        WHERE genre1='Animation'
        ORDER BY Rating desc
        LIMIT 5;
    """


with DAG(
    "calculate_popular_movies",
    schedule_interval=None,
    start_date=datetime(2000, 1, 1),
    catchup=False,
) as dag:
    imdb_movies = aql.load_file(
        File("https://raw.githubusercontent.com/astronomer/astro-sdk/main/tests/data/imdb_v2.csv"),
        output_table=Table(conn_id="sqlite_default"),
    )
    top_five_animations(
        input_table=imdb_movies,
        output_table=Table(name="top_animation"),
    )
