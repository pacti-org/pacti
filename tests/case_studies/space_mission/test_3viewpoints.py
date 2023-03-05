import nbformat
import os
from nbconvert.preprocessors import ExecutePreprocessor


def _read_notebook(filename: str):
    with open(filename) as ff:
        return nbformat.read(ff, nbformat.NO_CONVERT)

def _delete_if_exists(filename: str):
    if os.path.exists(filename):
        os.remove(filename)

j1 = 'case_studies/space_mission/json/scenario_power.json'
j2 = 'case_studies/space_mission/json/scenario_science.json'
j3 = 'case_studies/space_mission/json/scenario_nav.json'

def test_viewpoints():
    assert os.path.isdir('case_studies/space_mission/json')

    _delete_if_exists(j1)
    nb1 = _read_notebook('case_studies/space_mission/space_mission_power.ipynb')

    _delete_if_exists(j2)
    nb2 = _read_notebook('case_studies/space_mission/space_mission_science.ipynb')
    
    _delete_if_exists(j3)
    nb3 = _read_notebook('case_studies/space_mission/space_mission_navigation.ipynb')
    
    nb4 = _read_notebook('case_studies/space_mission/space_mission_3viewpoints.ipynb')
    
    
    ep = ExecutePreprocessor(timeout=600, kernel_name='python3')

    # Run the 1st notebook and write the scenario
    r1 = ep.preprocess(nb1)
    assert os.path.exists(j1)
    
    # Run the 2nd notebook and write the scenario
    r2 = ep.preprocess(nb2)
    assert os.path.exists(j2)

    # Run the 3rd notebook and write the scenario
    r3 = ep.preprocess(nb3)
    assert os.path.exists(j3)

    # This should read all 3 scenario json files and analyze them.
    r4 = ep.preprocess(nb4)
    print(r4)