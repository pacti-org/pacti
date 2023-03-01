
from pacti.terms.polyhedra import PolyhedralContract
from pacti.terms.polyhedra.serializer import write_contract

TEST_DATA_DIR = "tests/test_data/polyhedral_contracts/"


def test_composition_1():
    c = PolyhedralContract.from_file(TEST_DATA_DIR + "test_composition_1.json")
    expected = c[2]
    obtained = c[0].compose(c[1])
    print(expected)
    print(obtained)
    assert expected == obtained

if __name__ == "__main__":
    test_composition_1()
