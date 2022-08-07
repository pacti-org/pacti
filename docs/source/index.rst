.. Gear documentation master file, created by
   sphinx-quickstart on Sun Jul 31 13:14:31 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


Gear
====

Gear is a Python package for carrying out compositional system analysis and
design. Gear reasons about components specifications in a system using assume-guarantee
contracts. Gear's capabilities include:

- Verifying whether a component meets a specification.
- Obtaining sensible system specifications from the specifications of their
  subsystems.
- Computing specifications of elements that need to be added to a design in
  order to meet an objective.


Installing
----------

As Gear is in development, we use pip to install the package using the current development directory. Install and update using `pip`_:

.. code-block:: text

    $ pip install -e .

.. _pip: https://pip.pypa.io/en/stable/getting-started/

The installation will provide access to the command-line tool :code:`gear` and to the the Python package of the same name. Any updates to the dev folder :code:`src/gear` will immediately be available in the system.



Examples
--------

Composition
+++++++++++

Suppose we have the following system:

.. image:: _static/circuit_series_composition.svg
   :width: 400

Components :math:`M` and :math:`M'` obey, respectively, contracts :math:`C = (|i| \le 2, o \le i \le 2o + 5)` and :math:`C' = (-1 \le o \le 1/3, o' \le o)`. We can use gear to obtain the specification of the system by executing the command

.. code:: 

   gear examples/example.json result.json

Gear places the result of composition in the file result.json. The output is

.. code:: 

   Composed contract:
   InVars: {<Var i>}
   OutVars:{<Var o_p>}
   A: 3*i <= 1, -1*i <= 2
   G: 1*o_p + -1*i <= 0

Quotient
++++++++

Now we consider an example of quotient. Consider the following circuits:

.. image:: _static/circuit_series_quotient.svg
   :width: 400

We wish to implement a system :math:`M` with specification :math:`C = (i \le 1, o' \le 2i)`, and to do this we have available a component :math:`M'` with specification :math:`C' = (i \le 2, o \le 2i)`. We use the quotient operation in gear to obtain the specification of the component that we are missing so that the resulting object meets the specification :math:`C`. We run the command

.. code:: 

   gear examples/example_quotient.json result.json

And gear outputs

.. code:: 

   Contract quotient:
   InVars: {<Var o>}
   OutVars:{<Var o_p>}
   A: 1/2*o <= 1
   G: -1*o + 1*o_p <= 1



Contents
--------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
