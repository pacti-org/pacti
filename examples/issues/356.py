from pacti.contracts import PolyhedralIoContract

import logging

FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
logging.basicConfig(filename="../pacti.log", filemode="w", level=logging.DEBUG, format=FORMAT)

contractA = PolyhedralIoContract.from_strings(
    input_vars = ["soc_0"],
    output_vars = ["soc_1", "soc_2"],
    assumptions = ["soc_0 = 200"],
    guarantees = ["soc_1 >= 40",
                  "soc_2 >= 40"
                  ],
)

contractB = PolyhedralIoContract.from_strings(
    input_vars=["soc_0", "SBO_duration_0", "DSN_duration_1"],
    output_vars=["soc_1", "soc_2"],
    assumptions=["SBO_duration_0 >= 150",
                 "DSN_duration_1 >= 50"
                ],
    guarantees=["soc_0 - soc_1 >= 0.1 * SBO_duration_0",
                "soc_0 - soc_1 <= 0.2 * SBO_duration_0",
                "soc_1 - soc_2 >= 2 * DSN_duration_1",
                "soc_1 - soc_2 <= 2.2 * DSN_duration_1"
                ],
)

quotientContract = contractA.quotient(contractB)

resultingSystemContract = quotientContract.compose(contractB)


print(quotientContract)

assert resultingSystemContract.refines(contractA)