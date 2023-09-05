import glob

import pytest

from pacti.contracts import PolyhedralIoContract
from pacti.utils import read_contracts_from_file
from pacti.utils.errors import IncompatibleArgsError

TEST_DATA_DIR = "tests/test_data/polyhedral_contracts"

import logging

FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
logging.basicConfig(filename="../pacti.log", filemode="w", level=logging.DEBUG, format=FORMAT)

composition_test_instances = glob.glob(TEST_DATA_DIR + "**/*composition_success*.json", recursive=True)


@pytest.mark.parametrize("test_instance", composition_test_instances)
def test_composition_success(test_instance: str) -> None:
    try:
        c, _ = read_contracts_from_file(test_instance)
    except:
        assert False
    assert len(c) == 3
    expected = c[2].copy()
    try:
        obtained = c[0].compose(c[1])
    except:
        assert False
    print("*** Arg1")
    print(c[0])
    print("*** Arg2")
    print(c[1])
    print("*** Expected")
    print(expected)
    print("*** Obtained")
    print(obtained)
    assert expected == obtained


composition_failure_test_instances = glob.glob(TEST_DATA_DIR + "**/*composition_failure*.json", recursive=True)


@pytest.mark.parametrize("test_instance", composition_failure_test_instances)
def test_composition_failure(test_instance: str) -> None:
    try:
        c, _ = read_contracts_from_file(test_instance)
    except:
        assert False
    assert len(c) == 2
    with pytest.raises(IncompatibleArgsError):
        _ = c[0].compose(c[1])


composition_unsatisfiable_context_instances = glob.glob(
    TEST_DATA_DIR + "**/*composition_unsatisfiable_context*.json", recursive=True
)


@pytest.mark.parametrize("test_instance", composition_unsatisfiable_context_instances)
def test_composition_context(test_instance: str) -> None:
    try:
        c, _ = read_contracts_from_file(test_instance)
    except:
        assert False
    assert len(c) == 2
    with pytest.raises(ValueError, match="unsatisfiable in context"):
        _ = c[0].compose(c[1])


quotient_test_instances = glob.glob(TEST_DATA_DIR + "**/*quotient_success*.json", recursive=True)


@pytest.mark.parametrize("test_instance", quotient_test_instances)
def test_quotient_success(test_instance: str) -> None:
    try:
        c, _ = read_contracts_from_file(test_instance)
    except:
        assert False
    assert len(c) == 3
    expected = c[2]
    try:
        obtained = c[0].quotient(c[1], simplify=True)
    except:
        assert False
    assert expected == obtained
    assert expected <= obtained
    assert obtained <= expected


quotient_failure_test_instances = glob.glob(TEST_DATA_DIR + "**/*quotient_failure*.json", recursive=True)


@pytest.mark.parametrize("test_instance", quotient_failure_test_instances)
def test_quotient_failure(test_instance: str) -> None:
    try:
        c, _ = read_contracts_from_file(test_instance)
    except:
        assert False
    assert len(c) == 2
    with pytest.raises(IncompatibleArgsError):
        _ = c[0].quotient(c[1])


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
    assert expected == obtained


merging_failure_test_instances = glob.glob(TEST_DATA_DIR + "**/*merging_failure*.json", recursive=True)


@pytest.mark.parametrize("test_instance", merging_failure_test_instances)
def test_merging_failure(test_instance: str) -> None:
    try:
        c, _ = read_contracts_from_file(test_instance)
    except:
        assert False
    assert len(c) == 2
    with pytest.raises(IncompatibleArgsError):
        _ = c[0].merge(c[1])


refinement_test_instances = glob.glob(TEST_DATA_DIR + "**/*refinement*.json", recursive=True)


@pytest.mark.parametrize("test_instance", refinement_test_instances)
def test_refinement(test_instance: str) -> None:
    try:
        c, _ = read_contracts_from_file(test_instance)
    except:
        assert False
    assert len(c) == 2
    assert c[0] <= c[1]
    if c[0] != c[1]:
        assert not (c[1] <= c[0])


renaming_test_instances = glob.glob(TEST_DATA_DIR + "**/*rename*.json", recursive=True)


@pytest.mark.parametrize("test_instance", renaming_test_instances)
def test_refinement_1(test_instance: str) -> None:
    try:
        c, _ = read_contracts_from_file(test_instance)
    except:
        assert False
    assert len(c) == 2
    assert isinstance(c[0], PolyhedralIoContract)
    c_r = c[0].rename_variables([("p2_a", "p2_b"), ("p5_e", "p5_f")])
    assert c[1] == c_r


if __name__ == "__main__":
    file = r"tests/test_data/polyhedral_contracts/test_composition_success_Sal_lin_dCas9.json"
    test_composition_success(file)
