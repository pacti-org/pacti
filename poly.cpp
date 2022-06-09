
#include <ppl.hh>
#include <iostream>
#include <unordered_set>
#include <cassert>
#include "mathset.h"

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



class variable
{
private:
public:
  string name;
  variable(string name);
  bool operator==(const variable & other) const;
  friend ostream& operator<<(ostream& os, const variable& var);
};

variable::variable(string name)
{
  this->name = name;
}


bool variable::operator==(const variable & other) const {
  return this->name == other.name;
}

ostream& operator<<(ostream& os, const variable& var)
{
    os << "Var: " << var.name << " ";
    return os;
}

// custom specialization of std::hash can be injected in namespace std
template<>
struct std::hash<variable>
{
    std::size_t operator()(variable const& s) const noexcept
    {
        std::size_t h1 = std::hash<std::string>{}(s.name);
        return h1; // or use boost::hash_combine
    }
};

using VarSet = mathset<variable>;


class Term
{
private:
  /* data */
public:
  virtual VarSet* getvars() const = 0;
  virtual bool operator==(const Term & other) const = 0;
  virtual void eliminateVariable(variable& var) = 0;
  /* This is a string that will be hashed to implement unordered lists */
  virtual string hashstr() const = 0;
  virtual ~Term();
};

Term::~Term(){}

// custom specialization of std::hash can be injected in namespace std
template<>
struct std::hash<Term>
{
    std::size_t operator()(Term const& s) const noexcept
    {
        std::size_t h1 = std::hash<std::string>{}(s.hashstr());
        return h1; // or use boost::hash_combine
    }
};


class TermList: public mathset<Term*> {
  public:
    VarSet* getVars() const;
    VarSet* sharedVariables(const TermList* other) const;
    TermList* getTermsWithVars(const VarSet & vars);
    virtual TermList* simplifyWithTerms(const TermList* otherTems) const = 0;
};


VarSet* TermList::getVars() const{
  VarSet* result = new VarSet();
  typename mathset<Term*> :: iterator itr;
  for (auto itr = this->begin(); itr != this->end(); itr++) {
    result = result->setunion((*itr)->getvars());
  }
  return result;
}

TermList* TermList::getTermsWithVars(const VarSet & vars) {
  TermList* result;
  result->clear();

  typename mathset<Term*> :: iterator itr;
  for (auto itr = this->begin(); itr != this->end(); itr++) {
    if (! (*itr)->getvars()->isdisjoint(&vars)) {
      result->insert(*itr);
    }
  }
  return result;
}


VarSet* TermList::sharedVariables(const TermList* other) const {
  VarSet* varIntersection = this->getVars()->setint(other->getVars());
  return varIntersection;
}




class IoContract
{
private:
  VarSet* inputs;
  VarSet* outputs;
  TermList* assumptions;
  TermList* guarantees;
public:
  IoContract(VarSet* in, VarSet* out, TermList* assmpt, TermList* gtees) {
    inputs = in; outputs = out; assumptions = assmpt; guarantees = gtees;
  }
  //~IoContract();
  VarSet* getInputs() const {return this->inputs;}
  VarSet* getOutputs() const {return this->outputs;}
  TermList* getAssumptions() const {return this->assumptions;}
  TermList* getGuarantees() const {return this->guarantees;}
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
  TermList* assumptions_a = this->getAssumptions();
  TermList* assumptions_b = other->getAssumptions();
  TermList* guarantees_a = this->getGuarantees();
  TermList* guarantees_b = other->getGuarantees();

  TermList* assumptions_comp;
  if (! assumptions_a->sharedVariables(guarantees_b)->setint(varsNotInAssumptions)->empty()) {
    assumptions_comp = static_cast<TermList *> (assumptions_a->simplifyWithTerms(guarantees_b)->setunion(assumptions_b));
  } else if (! assumptions_b->sharedVariables(guarantees_a)->setint(varsNotInAssumptions)->empty())
  {
    assumptions_comp = static_cast<TermList *> (assumptions_b->simplifyWithTerms(guarantees_a)->setunion(assumptions_a));
  }
  /* compute guarantees */
  TermList* guarantees_comp;
  guarantees_comp = static_cast<TermList *> (guarantees_a->setunion(guarantees_b))->simplifyWithTerms(assumptions_comp);

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
    //unordered_set <int> hola;

    mathset<int> *hola = new mathset<int>;
    hola->insert(1);
    hola->insert(2);
    hola->insert(3);
    hola->insert(5);
    cout << "Hola\n";
    hola->print();
    mathset<int> * hola2 = new mathset<int> {2,3,3, 5, 4,5};
    hola2->print();
    mathset<int> *hola3 = hola->setint(hola2);
    cout << "Intersection is ";
    hola3->print();
    mathset<int> *hola4 = hola->setunion(hola2);
    cout << "Union is ";
    hola4->print();
    mathset<int> *hola5 = hola->setdiff(hola2);
    cout << "Diff is ";
    hola5->print();

    // creating a set of variables
    mathset<variable> * varset = new mathset<variable>;
    varset->insert(variable("a"));
    varset->insert(variable("b"));
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