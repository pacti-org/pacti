from pacti.contracts import PolyhedralIoContract
import logging

FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
logging.basicConfig(filename="../pacti.log", filemode="w", level=logging.DEBUG, format=FORMAT)

c1 = PolyhedralIoContract.from_strings(
    input_vars = ["Sal", "aTc"],
    output_vars = ["RFP"],
    assumptions = [
        "-Sal <= -0.909",
        "Sal <= 42.57",
        "-aTc <= -0.001818",
        "aTc <= 0.01287",
    ],
    guarantees = [
        "RFP <= 0.0049"
    ]
)

c0 = PolyhedralIoContract.from_strings(
input_vars = ["Sal", "aTc"],
output_vars = ["xRFP", "dCas9"],
assumptions = [
  "Sal <= 43.0",
  "-Sal <= -0.90",
  "aTc <= 0.013",
  "-aTc <= -0.0018"
],
guarantees = [
  "0.03 Sal - xRFP = -0.023",
  "88.84 aTc - dCas9 = -0.15"
]
)

print(c1)
print(c0)



cq = c1.quotient(c0)
print(cq)