import glob

import pytest

from pacti.utils import read_contracts_from_file
from pacti.iocontract import Var

TEST_DATA_DIR = "tests/test_data/behavior_contracts"

import logging

FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
logging.basicConfig(filename="../pacti.log", filemode="w", level=logging.DEBUG, format=FORMAT)

behavior_test_instances = glob.glob(TEST_DATA_DIR + "**/*behavior*.json", recursive=True)

x = Var("x")
y = Var("y")
test_success_combinations = {'tests/test_data/behavior_contracts/test_behavior_1.json': {x:0, y:2}}
test_failure_combinations = {'tests/test_data/behavior_contracts/test_behavior_1.json': {x:3, y:5}}

@pytest.mark.parametrize("test_instance", behavior_test_instances)
def test_contains_behavior_success(test_instance: str) -> None:
    try:
        c, _ = read_contracts_from_file(test_instance)
    except:
        assert False
    assert len(c) == 1
    contract = c[0]
    try:
        a_contains = contract.a.contains_behavior(test_success_combinations[test_instance])
        g_contains = contract.g.contains_behavior(test_success_combinations[test_instance])
    except:
        assert False
    assert a_contains == True
    assert g_contains == True

@pytest.mark.parametrize("test_instance", behavior_test_instances)
def test_contains_behavior_failure(test_instance: str) -> None:
    try:
        c, _ = read_contracts_from_file(test_instance)
    except:
        assert False
    assert len(c) == 1
    contract = c[0]
    try:
        a_contains = contract.a.contains_behavior(test_failure_combinations[test_instance])
        g_contains = contract.g.contains_behavior(test_failure_combinations[test_instance])
    except:
        assert False
    assert a_contains == False
    assert g_contains == False

if __name__ == "__main__":
    file = 'test_data/behavior_contracts/test_behavior_1.json'
    test_contains_behavior_success(file)
