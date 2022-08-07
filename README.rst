Gear
====

Gear is a Python package for carrying out compositional system analysis and
design. Gear represents components in a system using assume-guarantee
specifications, or contracts. Gear's capabilities include:

- Verifying whether a component meets a specification.
- Obtaining sensible specifications systems from the specification of their
  subsystems.
- Computing specifications of elements that need to be added to a design in
  order to meet an objective.


Installing
----------

As Gear is in development, we use pip to install the package using the current development directory. Install and update using `pip`_:

.. code-block:: text

    $ pip install -e .

.. _pip: https://pip.pypa.io/en/stable/getting-started/

The installation will provide access to the command-line tool :code:`gear` and to the the Python package of the same name. It's okay to run the install process using admin privileges.

A Simple Example
----------------

Suppose we have the following system:

External hyperlinks, like Python_.

.. _Python: docs/_build/html/index.html


Links
-----

-   `Documentation <docs/_build/html/index.html>`_
-   Source Code: https://github.com/iincer/contractTool