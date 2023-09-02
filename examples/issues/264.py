from pacti.contracts import PolyhedralIoContract

contract1 = PolyhedralIoContract.from_strings(
    input_vars=["i"],
    output_vars=[],
    assumptions=["|i| <= 1.234567e-5"],
    guarantees=[])

print(contract1)