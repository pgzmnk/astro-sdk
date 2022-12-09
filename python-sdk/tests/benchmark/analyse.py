#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import settings as benchmark_settings
from google.cloud import storage
from sqlalchemy import text

from astro.databases import create_database
from astro.table import Metadata, Table

SUMMARY_FIELDS = [
    "database",
    "dataset",
    "total_time",
    "memory_rss",
    "cpu_time_user",
    "cpu_time_system",
]

if sys.platform == "linux":
    SUMMARY_FIELDS.append("memory_pss")
    SUMMARY_FIELDS.append("memory_shared")


def format_bytes(bytes_):
    if abs(bytes_) < 1000:
        return str(bytes_) + "B"
    elif abs(bytes_) < 1e6:
        return str(round(bytes_ / 1e3, 2)) + "kB"
    elif abs(bytes_) < 1e9:
        return str(round(bytes_ / 1e6, 2)) + "MB"
    else:
        return str(round(bytes_ / 1e9, 2)) + "GB"


def format_time(time):
    if time < 1:
        return str(round(time * 1000, 2)) + "ms"
    if time < 60:
        return str(round(time, 2)) + "s"
    if time < 3600:
        return str(round(time / 60, 2)) + "min"
    else:
        return str(round(time / 3600, 2)) + "hrs"


def check_gcs_path(results_filepath):
    url_obj = urlparse(results_filepath)

    if url_obj.scheme == "gs":
        return True
    return False


def download_files_from_gcs(results_filepath):
    """Downloads folder from the GCS bucket."""

    gs_url = urlparse(results_filepath)
    bucket_name = gs_url.netloc
    source_blob_name = gs_url.path

    local_destination_file_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
        source_blob_name[1:],
    )
    if os.path.exists(os.path.dirname(local_destination_file_path)):
        os.remove(local_destination_file_path)
    else:
        os.mkdir(os.path.dirname(local_destination_file_path))
    local_file = Path(local_destination_file_path)
    local_file.touch(exist_ok=True)

    storage_client = storage.Client()

    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(source_blob_name[1:])

    blob.download_to_filename(local_destination_file_path)

    print(
        f"Downloaded storage object {source_blob_name}  from bucket {bucket_name} to local"
        f" file {local_destination_file_path}."
    )

    return local_destination_file_path


def analyse_results_from_file(results_filepath: str, output_filepath: str):
    data = []
    with open(results_filepath) as fp:
        for line in fp.readlines():
            data.append(json.loads(line.strip()))

    df = pd.json_normalize(data, sep="_")
    analyse_results(df, output_filepath)


def import_profile_data_to_bq(
    bq_git_sha: str, conn_id: str = benchmark_settings.publish_benchmarks_db_conn_id
):
    """Import profile data to bigquery table

    :param bq_git_sha: bq_git_sha used to filter records
    :param conn_id: Airflow's connection id to be used to publish the profiling data
    """
    db = create_database(conn_id)
    table = Table(
        name=benchmark_settings.publish_benchmarks_table,
        metadata=Metadata(schema=benchmark_settings.publish_benchmarks_schema),
    )

    return db.export_table_to_pandas_dataframe(
        table,
        select_kwargs={
            "whereclause": text(f'{benchmark_settings.publish_benchmarks_table_grouping_col}="{bq_git_sha}"')
        },
    )


def analyse_results_from_database(bq_git_sha: str, output_filepath: str):
    df = import_profile_data_to_bq(bq_git_sha=bq_git_sha)
    analyse_results(df, output_filepath)


def analyse_results(df: pd.DataFrame, output_filepath: str = None):
    # calculate total CPU from process & children
    mean_by_dag = df.groupby("dag_id", as_index=False).mean()

    # format data
    mean_by_dag["database"] = mean_by_dag.dag_id.apply(lambda text: text.split("into_")[-1])
    mean_by_dag["dataset"] = mean_by_dag.dag_id.apply(
        lambda text: text.split("load_file_")[-1].split("_into")[0]
    )

    # We should consider removing lambda function
    # skipcq need because of lambda function
    mean_by_dag["memory_rss"] = mean_by_dag.memory_full_info_rss.apply(
        lambda value: format_bytes(value)  # skipcq PYL-W0108
    )
    # We should consider removing lambda function
    # skipcq need because of lambda function
    if sys.platform == "linux":
        mean_by_dag["memory_pss"] = mean_by_dag.memory_full_info_pss.apply(
            lambda value: format_bytes(value)
        )  # skipcq PYL-W0108
        mean_by_dag["memory_shared"] = mean_by_dag.memory_full_info_shared.apply(
            lambda value: format_bytes(value)  # skipcq PYL-W0108
        )

    # We should consider removing lambda function
    # skipcq need because of lambda function
    mean_by_dag["total_time"] = mean_by_dag["duration"].apply(
        lambda ms_time: format_time(ms_time)  # skipcq PYL-W0108
    )

    # We should consider removing lambda function
    # skipcq need because of lambda function
    mean_by_dag["cpu_time_system"] = (
        mean_by_dag["cpu_time_system"] + mean_by_dag["cpu_time_children_system"]
    ).apply(
        lambda ms_time: format_time(ms_time)  # skipcq PYL-W0108
    )

    # We should consider removing lambda function
    # skipcq need because of lambda function
    mean_by_dag["cpu_time_user"] = (
        mean_by_dag["cpu_time_user"] + mean_by_dag["cpu_time_children_user"]
    ).apply(
        lambda ms_time: format_time(ms_time)  # skipcq PYL-W0108
    )

    summary = mean_by_dag[SUMMARY_FIELDS]
    content = get_content(summary)
    if output_filepath:
        with open(output_filepath, "w") as file:
            file.write(content)
    else:
        print(content)


def get_content(summary):
    content = ""
    # print Markdown tables per database
    for database_name in summary["database"].unique().tolist():
        content = content + f"\n\n### Database: {database_name}\n"
        content = content + str(summary[summary["database"] == database_name].to_markdown(index=False))
    return content


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trigger benchmark DAG")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--results-filepath",
        "-r",
        type=str,
        help="NDJSON local path (/path/to/file.ndjson) or Google "
        "cloud storage path (gs://bucket/sample.ndjson) containing the results for a benchmark run",
    )
    group.add_argument(
        "--bq-git-sha",
        "-b",
        type=str,
        help=f"Use to render benchmarking markdown from data stored in bigquery "
        f"table({benchmark_settings.publish_benchmarks_schema}.{benchmark_settings.publish_benchmarks_table})."
        f" The data that qualifies for the generation will be filtered by Git SHA. Use initial 7 letters of a commit."
        f" Matched against {benchmark_settings.publish_benchmarks_table_grouping_col} col.",
    )
    parser.add_argument(
        "--output-filepath",
        "-o",
        type=str,
        required=False,
        help="File path to create markdown file",
    )
    args = parser.parse_args()
    results_filepath = args.results_filepath
    bq_git_sha = args.bq_git_sha
    output_filepath = args.output_filepath
    print(f"Running the analysis on {results_filepath}...")
    if results_filepath:
        if check_gcs_path(results_filepath):
            results_filepath = download_files_from_gcs(results_filepath)
        analyse_results_from_file(results_filepath, output_filepath)
    elif bq_git_sha:
        analyse_results_from_database(bq_git_sha, output_filepath)
