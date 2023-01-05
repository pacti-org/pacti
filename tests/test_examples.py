import os


def test_examples():
    result = os.popen("jupyter nbconvert --to script --execute --stdout examples/AND_logic_gate.ipynb | python3").read()
    assert result[-1] == "\n"
