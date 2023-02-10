
from pacti.terms.polyhedra.loaders import pt_from_string

terms=["-3.0e+x<=4", 
       "-3.0e1e-1x <= -2.3", 
       "-3.0e1 e - x+z <= 3.0e-1", 
       "-3.0*e + 4x-7z<=0.0", 
       "-3.0*e4<=1",
       "-3.0e5<=3",
       "-3.0 * e<=4",
       "-3.0 * e_1-4y<=0"]
for t in terms:
  print(f"\nterm: {t}")
  p=pt_from_string(t)
  print(p)
