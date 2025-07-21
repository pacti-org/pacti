

from pacti.contracts import PolyhedralIoContract

import logging


FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
logging.basicConfig(filename="../pacti.log", filemode="w", level=logging.DEBUG, format=FORMAT)




C_sys = PolyhedralIoContract.from_strings(
    input_vars=[
        "x"
    ],
    output_vars=["f"],
    assumptions=[
        "x <= 1"
    ],
    guarantees=[
       "f >= 5"
    ]
)

C_1 = PolyhedralIoContract.from_strings(
    input_vars=[
        "x",
        "b"
    ],
    output_vars=["f"],
    assumptions=[

        # "x <= 1"
   
    ],
    guarantees=[
        "f = b - x"
      
    ]
)

quotientContract = C_sys.quotient(C_1)
resultingSystemContract = quotientContract.compose(C_1)

print(C_sys.quotient(C_1))
assert resultingSystemContract.refines(C_sys)


