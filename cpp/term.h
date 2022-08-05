

#ifndef TERM_H
#define TERM_H

#include "mathset.h"
#include "designvar.h"

class Term
{
private:
  /* data */
public:
  virtual VarSet* getvars() const = 0;
  virtual bool operator==(const Term & other) const = 0;
  /* This is a string that will be hashed to implement unordered lists */
  virtual std::string hashstr() const = 0;
  inline virtual ~Term();
};

Term::~Term(){}

namespace std {
// custom specialization of std::hash can be injected in namespace std
template<>
struct hash<Term>
{
    size_t operator()(Term const& s) const noexcept
    {
        size_t h1 = hash<string>{}(s.hashstr());
        return h1; // or use boost::hash_combine
    }
};
}


class TermSet: public mathset<Term*> {
  public:
    inline VarSet* getVars() const;
    inline VarSet* sharedVariables(const TermSet* other) const;
    inline TermSet* getTermsWithVars(const VarSet & vars);
    virtual TermSet* simplifyWithTerms(const TermSet* otherTems, const VarSet* varsToElim) const = 0;
};


VarSet* TermSet::getVars() const{
  VarSet* result = new VarSet();
  typename mathset<Term*> :: iterator itr;
  for (auto itr = this->begin(); itr != this->end(); itr++) {
    result = result->setunion((*itr)->getvars());
  }
  return result;
}

TermSet* TermSet::getTermsWithVars(const VarSet & vars) {
  TermSet* result;
  result->clear();

  typename mathset<Term*> :: iterator itr;
  for (auto itr = this->begin(); itr != this->end(); itr++) {
    if (! (*itr)->getvars()->isdisjoint(&vars)) {
      result->insert(*itr);
    }
  }
  return result;
}


VarSet* TermSet::sharedVariables(const TermSet* other) const {
  VarSet* varIntersection = this->getVars()->setint(other->getVars());
  return varIntersection;
}

#endif