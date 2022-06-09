#ifndef DESIGNVAR_H
#define DESIGNVAR_H

#include "mathset.h"
#include <iostream>

class designvar
{
private:
public:
  std::string name;
  inline designvar(std::string name);
  inline bool operator==(const designvar & other) const;
  inline friend std::ostream& operator<<(std::ostream& os, const designvar& var);
};

designvar::designvar(std::string name)
{
  this->name = name;
}


bool designvar::operator==(const designvar & other) const {
  return this->name == other.name;
}

std::ostream& operator<<(std::ostream& os, const designvar& var)
{
    os << "Var: " << var.name << " ";
    return os;
}

// custom specialization of std::hash can be injected in namespace std
template<>
struct std::hash<designvar>
{
    std::size_t operator()(designvar const& s) const noexcept
    {
        std::size_t h1 = std::hash<std::string>{}(s.name);
        return h1; // or use boost::hash_combine
    }
};

using VarSet = mathset<designvar>;


#endif