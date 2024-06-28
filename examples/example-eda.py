
import pyeda.boolalg.exprnode
from pyeda.inter import *



import pyeda.boolalg

import copy


f = expr("a & b | a & c | b & c | ~a")
fast = f.to_ast()

g = expr("a")


print(f"The variables in f are: {f.inputs}")
print(f.inputs)
print(f.xs)
var = f.inputs[0]

print(type(var))

print(var)

print(str(f))

avar = Variable(names='b',indices=())
avar = exprvar('z')

print(avar)

f.consensus(vs=(var))
f.consensus(vs=(avar))


g = copy.copy(f)
print(g)

h = expr('~(~a)')
i = expr('a => c') 

a_var = exprvar('a')
aa_var = exprvar('a')
print(a_var)
print(aa_var)
print(a_var == aa_var)

def rename_expr(expression, oldvar, newvar):
    if isinstance(expression, pyeda.boolalg.expr.Atom):
        if isinstance(expression, pyeda.boolalg.expr.Variable):
            if expression == oldvar:
                return newvar
        if isinstance(expression, pyeda.boolalg.expr.Complement):
            if expression == pyeda.boolalg.expr.Not(oldvar):
                return pyeda.boolalg.expr.Not(newvar)
        return expression
    elif isinstance(expression, pyeda.boolalg.expr.NotOp):
        nxs = pyeda.boolalg.expr.Expression.box(rename_expr(expression.xs[0], oldvar, newvar)).node
        return pyeda.boolalg.expr._expr(pyeda.boolalg.exprnode.not_(nxs))
    elif isinstance(expression, pyeda.boolalg.expr.ImpliesOp):
        nxs = [pyeda.boolalg.expr.Expression.box(rename_expr(x, oldvar, newvar)).node for x in expression.xs]
        return pyeda.boolalg.expr._expr(pyeda.boolalg.exprnode.impl(*nxs))
    elif isinstance(expression, pyeda.boolalg.expr.AndOp):
        nxs = [pyeda.boolalg.expr.Expression.box(rename_expr(x, oldvar, newvar)).node for x in expression.xs]
        return pyeda.boolalg.expr._expr(pyeda.boolalg.exprnode.and_(*nxs))
    elif isinstance(expression, pyeda.boolalg.expr.OrOp):
        nxs = [pyeda.boolalg.expr.Expression.box(rename_expr(x, oldvar, newvar)).node for x in expression.xs]
        return pyeda.boolalg.expr._expr(pyeda.boolalg.exprnode.or_(*nxs))
    else:
        raise ValueError()

print("----------------")

print(rename_expr(avar,avar,var))
print(rename_expr(h,var,avar))
print(rename_expr(i,var,avar))
print(rename_expr(f,var,avar))

