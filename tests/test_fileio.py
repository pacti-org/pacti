
import tempfile
from pacti.utils import read_contracts_from_file, write_contracts_to_file


def test_basic_fileio():
    io_poly_compound = "tests/test_data/compound_contracts/test_merging_success_multiagent_1.json"
    io_poly = "tests/test_data/polyhedral_contracts/test_quotient_success_1.json"


    c_list, c_names = read_contracts_from_file(io_poly)
    tempfile_name = tempfile.NamedTemporaryFile().name

    for machine in [True, False]:
        write_contracts_to_file(c_list, c_names, file_name=tempfile_name, machine_representation=machine)
        c_list_read, c_names_read = read_contracts_from_file(tempfile_name)
        for i in range(len(c_list)):
            assert c_list_read[i] == c_list[i]
        assert c_names_read == c_names

    c_list, c_names = read_contracts_from_file(io_poly_compound)
    write_contracts_to_file(c_list, c_names, file_name=tempfile_name, machine_representation=False)
    c_list_read, c_names_read = read_contracts_from_file(tempfile_name)
    for i in range(len(c_list)):
        assert c_list_read[i] == c_list[i]
    assert c_names_read == c_names

if __name__ == "__main__":
    test_basic_fileio()

    