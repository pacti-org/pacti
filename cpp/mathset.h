

#ifndef MSET_H
#define MSET_H

#include <unordered_set>
//using namespace std;

/* Implementations for set operations */
template <typename T>
class mathset: public std::unordered_set<T> {
    public:
    using std::unordered_set<T>::unordered_set;
    /* Binary operations on sets */
    mathset<T>* setint(const mathset<T> * other) const;
    mathset<T>* setunion(const mathset<T> * other) const;
    mathset<T>* setdiff(const mathset<T> * other) const;
    /* Relations */
    // say if set contains element
    bool contains(const T* element) const;
    // say if two sets are disjoint
    bool isdisjoint(const mathset<T> * other) const; 
    /* Printing. Depends on T supporting << */
    void print();
};

template <class T>
bool mathset<T>::contains(const T* element) const {
  return this->find(*element) != this->end();
}

template <class T>
bool mathset<T>::isdisjoint(const mathset<T> * other) const {
  return this->setint(other)->empty();
}


template <class T>
mathset<T>* mathset<T>::setint(const mathset<T> * other) const {
  mathset<T> * result = new mathset<T>;
  const mathset<T>* basea;
  const mathset<T>* baseb;

  basea = this;
  baseb = other;
  if (other->size() < this->size()) {
    basea = other;
    baseb = this; 
  }

  typename mathset<T> :: iterator itr;
  
  for (auto itr = basea->begin(); itr != basea->end(); itr++) {
    if (baseb->contains(&*itr)) {
      result->insert(*itr);
    }
  }
  return result;
}

template <class T>
mathset<T>* mathset<T>::setunion(const mathset<T> * other) const {
  mathset<T> * result = new mathset<T>;

  typename mathset<T> :: iterator itr;
  for (auto itr = this->begin(); itr != this->end(); itr++) {
    result->insert(*itr);
  }
  for (auto itr = other->begin(); itr != other->end(); itr++) {
    result->insert(*itr);
  }
  return result;
}

template <class T>
mathset<T>* mathset<T>::setdiff(const mathset<T> * other) const {
  mathset<T> * result = new mathset<T>;

  typename mathset<T> :: iterator itr;
  for (auto itr = this->begin(); itr != this->end(); itr++) {
    if (!other->contains(&*itr)) {
      result->insert(*itr);
    }
  }
  return result;
}

template <class T>
void mathset<T>::print() {
  typename mathset<T> :: iterator itr;
  for (auto itr = this->begin(); itr != this->end(); itr++) {
    std::cout << *itr << " ";
  }
  std::cout << "\n";
}

#endif

