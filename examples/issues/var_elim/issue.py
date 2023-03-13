


from pacti import read_contracts_from_file


conts, _ = read_contracts_from_file("var_elim.json")

result = conts[0].compose(conts[1])
