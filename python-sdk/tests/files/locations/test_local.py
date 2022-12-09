from __future__ import annotations

import os
import pathlib
import shutil
import uuid

import pytest

from astro.constants import FileLocation
from astro.files.locations.base import BaseFileLocation
from astro.files.locations.local import LocalLocation

CWD = pathlib.Path(__file__).parent

LOCAL_FILEPATH = f"{CWD}/../../data/homes2.csv"
LOCAL_DIR = f"/tmp/{uuid.uuid4()}/"
LOCAL_DIR_FILE_1 = str(pathlib.Path(LOCAL_DIR, "file_1.txt"))
LOCAL_DIR_FILE_2 = str(pathlib.Path(LOCAL_DIR, "file_2.txt"))

sample_filepaths_per_location = [
    (FileLocation.LOCAL, LOCAL_FILEPATH),
]
sample_file = pathlib.Path(pathlib.Path(__file__).parent.parent.parent, "data/sample.csv")


@pytest.fixture()
def local_dir():
    """create temp dir"""
    os.mkdir(LOCAL_DIR)
    open(LOCAL_DIR_FILE_1, "a").close()
    open(LOCAL_DIR_FILE_2, "a").close()
    yield
    shutil.rmtree(LOCAL_DIR)


def test_get_location_type_with_supported_location():  # skipcq: PYL-W0612
    """With all the supported locations"""
    location = BaseFileLocation.get_location_type(LOCAL_FILEPATH)
    assert location == FileLocation.LOCAL


def test_get_location_type_with_unsupported_location_raises_exception():  # skipcq: PYL-W0612
    """With all the unsupported locations, should raise a valueError exception"""
    unsupported_filepath = "invalid://some-file"
    with pytest.raises(ValueError) as exc_info:
        _ = BaseFileLocation.get_location_type(unsupported_filepath)
    expected_msg = "Unsupported scheme 'invalid' from path 'invalid://some-file'"
    assert exc_info.value.args[0] == expected_msg


def test_get_transport_params_with_local():  # skipcq: PYL-W0612
    """with local filepath"""
    location = LocalLocation(LOCAL_FILEPATH)
    assert location.transport_params is None


@pytest.mark.parametrize("path", [LOCAL_DIR, LOCAL_DIR + "file_*"], ids=["without-prefix", "with-prefix"])
def test_get_paths_with_local_dir(local_dir, path):  # skipcq: PYL-W0612
    """with local filepath"""
    location = LocalLocation(path)
    assert sorted(location.paths) == [LOCAL_DIR_FILE_1, LOCAL_DIR_FILE_2]


def test_size():
    """Test get_size() of for local file."""
    assert LocalLocation(str(sample_file.absolute())).size == 65
