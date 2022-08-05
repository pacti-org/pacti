
#include <ppl.hh>
//#include <iostream>
#include <cassert>
#include "mathset.h"
#include "designvar.h"
#include "term.h"
#include "iocontract.h"

#define NDEBUG


using namespace std;

namespace pll = Parma_Polyhedra_Library;


void
print_constraints(const pll::Constraint_System& cs,
                  const std::string& intro) {
  if (!intro.empty())
    cout << intro << "\n";
  pll::Constraint_System::const_iterator i = cs.begin();
  pll::Constraint_System::const_iterator cs_end = cs.end();
  bool printed_something = i != cs_end;
  while (i != cs_end) {
    using IO_Operators::operator<<;
    cout << *i++;
    if (i != cs_end)
      cout << ",\n";
  }
  cout << (printed_something ? "." : "true.") << std::endl;
}

void
print_constraints(const Polyhedron& ph,
                  const std::string& intro) {
  print_constraints(ph.constraints(), intro);
}




int main() {
    mathset<int> *test = new mathset<int>;
    test->insert(1);
    test->insert(2);
    test->insert(3);
    test->insert(5);
    cout << "Tests begin\n";
    test->print();
    mathset<int> * test2 = new mathset<int> {2,3,3, 5, 4,5};
    test2->print();
    mathset<int> *test3 = test->setint(test2);
    cout << "Intersection is ";
    test3->print();
    mathset<int> *test4 = test->setunion(test2);
    cout << "Union is ";
    test4->print();
    mathset<int> *test5 = test->setdiff(test2);
    cout << "Diff is ";
    test5->print();

    // creating a set of variables
    mathset<designvar> * varset = new mathset<designvar>;
    varset->insert(designvar("a"));
    varset->insert(designvar("b"));
    varset->print();
    

    pll::Variable x(0);
    pll::Variable y(1);
    NNC_Polyhedron ph(3);
    //ph.add_constraint(y <= 10);
    //ph.add_constraint(x <= 5 + y);
    //ph.add_constraint(2*x >= y);
    //ph.add_constraint(y >= 2);
    ph.add_constraint(x+ y <= 2);
    ph.add_constraint(y >= 2);
    print_constraints(ph, "** before removal **");
    pll::Variables_Set to_remove;
    to_remove.insert(y);
    //to_remove.insert(x);
    ph.remove_space_dimensions(to_remove);
    print_constraints(ph, "** after removal **");

    
    return 0;
}