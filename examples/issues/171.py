from pacti.contracts import PolyhedralIoContract
import logging

FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
logging.basicConfig(filename="../pacti.log", filemode="w", level=logging.DEBUG, format=FORMAT)

C1 = PolyhedralIoContract.from_strings(
    input_vars   =["t0", "dt0"],
    output_vars  =["t1"],
    assumptions =["-t0 <= 0"],
    guarantees  =["t1 - t0 - dt0 = 0"])

C2 = PolyhedralIoContract.from_strings(
    input_vars   =[ "t1", "dt1" ],
    output_vars  =[ "t2" ],
    assumptions =[ "-t1 <= 0" ],
    guarantees  =[ "t2 - t1 - dt1 = 0" ])

C12 = C1.compose(C2)
print(C12)

TOP = PolyhedralIoContract.from_strings(
    input_vars   =[ "t0", "dt0", "dt1" ],
    output_vars  =["t2"],
    assumptions =["-t0 - dt0 <= 0", "-t0 <= 0"],
    guarantees  =["t2 - t0 - dt1 - dt0 = 0"])

Q = TOP.quotient(C1)
print(Q)