
#include <iostream>
#include "term.h"
#include "iocontract.h"


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