import glob

import pytest

from pacti.utils import read_contracts_from_file

TEST_DATA_DIR = "tests/test_data/compound_contracts"

import logging

# from ipdb import set_trace as st

FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
logging.basicConfig(filename="../pacti.log", filemode="w", level=logging.DEBUG, format=FORMAT)

merging_test_instances = glob.glob(TEST_DATA_DIR + "**/*merging_success*.json", recursive=True)


@pytest.mark.parametrize("test_instance", merging_test_instances)
def test_merging_success(test_instance: str) -> None:
    try:
        c, _ = read_contracts_from_file(test_instance)
    except:
        assert False
    assert len(c) == 3
    expected = c[2]
    try:
        obtained = c[0].merge(c[1])
    except:
        assert False
    # st()
    assert expected == obtained


merging_failure_test_instances = glob.glob(TEST_DATA_DIR + "**/*merging_failure*.json", recursive=True)


@pytest.mark.parametrize("test_instance", merging_failure_test_instances)
def test_merging_failure(test_instance: str) -> None:
    try:
        c, _ = read_contracts_from_file(test_instance)
    except:
        assert False
    assert len(c) == 2
    with pytest.raises(ValueError):
        _ = c[0].merge(c[1])


if __name__ == "__main__":
    file = "test_merging_success_multiagent_3.json"
    test_merging_success(file)
