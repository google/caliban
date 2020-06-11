Getting Caliban
---------------

.. NOTE:: If you're currently in a ``virtualenv``\ , please run ``deactivate``
   to disable it before proceeding.

We recommend installing ``caliban`` using `\ ``pipx``
<https://pypi.org/project/pipx/>`_. `\ ``pipx``
<https://pypi.org/project/pipx/>`_ is a tool that lets you install command line
utilities written in Python into their own virtual environments, completely
isolated from your system python packages or other virtualenvs.

You don't HAVE to do this - you can install caliban in your global environment,
or in a virtualenv - but ``pipx`` is the sanest way we've found to install
Python CLI command tools.

Install ``pipx`` into your global python environment like this:

.. code-block:: bash

   python3 -m pip install --user pipx
   python3 -m pipx ensurepath

Once ``pipx`` is installed, use it to install ``caliban``\. The next step is
slightly different, depending on if you have ``pipx < 0.15.0`` or ``pipx >=
0.15.0``:

.. code-block:: bash

   # Command for pipx < 0.15.0
   pipx install -e --spec git+https://github.com/google/caliban.git caliban

   # Command for pipx >= 0.15.0
   pipx install git+https://github.com/google/caliban.git

Upgrading Caliban
^^^^^^^^^^^^^^^^^

With ``pipx``\ , upgrading Caliban is simple. The following command will do it:

.. code-block:: bash

   pipx upgrade caliban

Check your Installation
^^^^^^^^^^^^^^^^^^^^^^^

To check if all is well, run

.. code-block:: bash

   caliban --help

to see the list of subcommands. We'll explore the meaning of each command below.
