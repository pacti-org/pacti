

#include <iostream>
#include "mathset.h"
#include "designvar.h"
#include "term.h"
#include "iocontract.h"

#define NDEBUG


using namespace std;




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
    
    return 0;
}