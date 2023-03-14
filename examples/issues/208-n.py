

from pacti.terms.polyhedra import PolyhedralTermList
import pacti.terms.polyhedra.serializer as serializer
from pacti.iocontract.iocontract import Var

import logging

FORMAT = "%(asctime)s:%(levelname)s:%(name)s:%(message)s"
logging.basicConfig(filename="../pacti.log", filemode="w", level=logging.DEBUG, format=FORMAT)



term = serializer.internal_pt_from_string("0.6 duration_tcm_deltav5 + 0.8 duration_tcm_heating4 - soc3_exit <= 0.0")[0]

context_str = [
  "-4.2 duration_dsn1 - output_soc1 + soc1_entry <= 0.0",
"3.8 duration_dsn1 + output_soc1 - soc1_entry <= 0.0",
"-4.0 duration_charging2 - output_soc1 + output_soc2 <= 0.0",
"3.0 duration_charging2 + output_soc1 - output_soc2 <= 0.0",
"output_soc2 <= 100.0",
"-1.4 duration_sbo3 + output_soc2 - soc3_exit <= 0.0",
"duration_sbo3 - output_soc2 + soc3_exit <= 0.0"]

context = PolyhedralTermList([serializer.internal_pt_from_string(ct)[0] for ct in context_str])


print(term)
print(context)

refined = PolyhedralTermList._transform_term(term, context, [Var("soc3_exit"), Var("output_soc2")], True)
print(refined)
