from pacti.terms.polyhedra import PolyhedralContract
import glob


TEST_DATA_DIR = "tests/test_data/polyhedral_contracts"



def test_composition():
    test_instances = glob.glob(TEST_DATA_DIR+"**/*composition*.json", recursive=True)
    for test_instance in test_instances:
        try:
            c = PolyhedralContract.from_file(test_instance)
        except:
            assert False
        assert len(c) == 3
        expected = c[2]
        try:
            obtained = c[0].compose(c[1])
        except:
            assert False
        assert expected == obtained


def test_quotient():
    test_instances = glob.glob(TEST_DATA_DIR+"**/*quotient*.json", recursive=True)
    for test_instance in test_instances:
        c = PolyhedralContract.from_file(test_instance)
        assert len(c) == 3
        expected = c[2]
        obtained = c[0].quotient(c[1])
        assert expected == obtained


def test_merging():
    test_instances = glob.glob(TEST_DATA_DIR+"**/*merging*.json", recursive=True)
    for test_instance in test_instances:
        c = PolyhedralContract.from_file(test_instance)
        assert len(c) == 3
        expected = c[2]
        obtained = c[0].merge(c[1])
        assert expected == obtained


def test_refinement():
    test_instances = glob.glob(TEST_DATA_DIR+"**/*refinement*.json", recursive=True)
    for test_instance in test_instances:
        c = PolyhedralContract.from_file(test_instance)
        assert len(c) == 2
        assert c[0] <= c[1]

