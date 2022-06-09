
#include <ppl.hh>
//#include <iostream>
#include <cassert>
#include "mathset.h"
#include "designvar.h"
#include "term.h"

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





class IoContract
{
private:
  VarSet* inputs;
  VarSet* outputs;
  TermSet* assumptions;
  TermSet* guarantees;
public:
  IoContract(VarSet* in, VarSet* out, TermSet* assmpt, TermSet* gtees) {
    inputs = in; outputs = out; assumptions = assmpt; guarantees = gtees;
  }
  //~IoContract();
  VarSet* getInputs() const {return this->inputs;}
  VarSet* getOutputs() const {return this->outputs;}
  TermSet* getAssumptions() const {return this->assumptions;}
  TermSet* getGuarantees() const {return this->guarantees;}
  IoContract* compose(IoContract * other);
};


IoContract* IoContract::compose(IoContract* other) {
  /* sanity checks: contracts don't share outputs */
  assert(this->getOutputs()->isdisjoint(other->getOutputs()));
  /* find input, output, and internal variables */
  VarSet* internalvars = this->getOutputs()->setint(other->getInputs())->setunion(
                    this->getInputs()->setint(other->getOutputs()));
  VarSet* outvars = this->getOutputs()->setunion(other->getOutputs())->setdiff(internalvars);
  VarSet* invars  = this->getInputs()->setunion(other->getInputs())->setdiff(internalvars)->setdiff(outvars);
  /* we remove (i) internal variables from guarantees & (ii) 
  both internal and output vars from the assumptions */
  VarSet* varsNotInAssumptions = outvars->setunion(internalvars);
  /* compute assumptions */
  TermSet* assumptions_a = this->getAssumptions();
  TermSet* assumptions_b = other->getAssumptions();
  TermSet* guarantees_a = this->getGuarantees();
  TermSet* guarantees_b = other->getGuarantees();

  TermSet* assumptions_comp;
  if (! assumptions_a->sharedVariables(guarantees_b)->setint(varsNotInAssumptions)->empty()) {
    assumptions_comp = static_cast<TermSet *> (assumptions_a->simplifyWithTerms(guarantees_b, varsNotInAssumptions)->setunion(assumptions_b));
  } else if (! assumptions_b->sharedVariables(guarantees_a)->setint(varsNotInAssumptions)->empty())
  {
    assumptions_comp = static_cast<TermSet *> (assumptions_b->simplifyWithTerms(guarantees_a, varsNotInAssumptions)->setunion(assumptions_a));
  }
  /* compute guarantees */
  TermSet* guarantees_comp;
  guarantees_comp = static_cast<TermSet *> (guarantees_a->setunion(guarantees_b))->simplifyWithTerms(assumptions_comp, internalvars);

  IoContract * result = new IoContract(invars, outvars, assumptions_comp, guarantees_comp);
  return result;
}









// class Constraint
// {
// private:
//     /* data */
// public:
//     Constraint
// (/* args */);
//     ~Constraint
// ();
// };

// Constraint::Constraint(/* args */)
// {
// }

// Constraint::~Constraint()
// {
// }


// class AgContract
// {
// private:
//     Variables inputVariables;
//     Variables outputVariables;
//     Constraints assumptions;
//     Constraints guarantees;
// public:
//     AgContract(/* args */);
//     ~AgContract();
//     AgContract compose(AgContract& other);
// };

// AgContract::AgContract(Variables& ivars, Variables& ovars, )
// {
// }

// AgContract::~AgContract()
// {
// }

// AgContract compose(AgContract& other) {
    
// }




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
    NNC_Polyhedron ph(4);
    ph.add_constraint(y <= 10);
    ph.add_constraint(x <= 5 + y);
    ph.add_constraint(2*x >= y);
    ph.add_constraint(y >= 2);
    print_constraints(ph, "** before removal **");
    pll::Variables_Set to_remove;
    to_remove.insert(y);
    ph.remove_space_dimensions(to_remove);
    print_constraints(ph, "** after removal **");

    
    return 0;
}