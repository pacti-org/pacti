

#ifndef IOCONTRACT_H
#define IOCONTRACT_H

#include "term.h"
#include <cassert>

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


#endif