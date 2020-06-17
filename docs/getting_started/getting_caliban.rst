Getting Caliban
---------------

.. warning:: If you're currently in a ``virtualenv``\ , please run ``deactivate``
   to disable it before proceeding.

We recommend installing ``caliban`` using `pipx
<https://pypi.org/project/pipx/>`_. `pipx <https://pypi.org/project/pipx/>`_ is
a tool that lets you install command line utilities written in Python into their
own virtual environments, completely isolated from your system python packages.

You don't HAVE to do this - you can install caliban in your global environment,
or in a virtualenv - but ``pipx`` is the sanest way we've found to install
Python CLI command tools.

.. NOTE:: Before you install Caliban, you'll need to visit the
          :doc:`prerequisites` page and make sure you have Docker installed and
          the correct version of Python 3.

Install ``pipx`` into your global python environment like this:

.. code-block:: bash

   python3 -m pip install --user pipx
   python3 -m pipx ensurepath

Once ``pipx`` is installed, use it to install ``caliban``:

.. code-block:: bash

   pipx install caliban

If you don't want to use `pipx`, install Caliban via pip:

.. code-block:: bash

   pip install -U caliban

Upgrading Caliban
^^^^^^^^^^^^^^^^^

With ``pipx``\ , upgrading Caliban is simple. The following command will do it:

.. code-block:: bash

   pipx upgrade caliban

If you've installed Caliban with pip:

.. code-block:: bash

   pip upgrade caliban

Check your Installation
^^^^^^^^^^^^^^^^^^^^^^^

To check if all is well, run

.. code-block:: bash

   caliban --help

To take Caliban through its paces, visit the `"Getting Started with Caliban"
<https://github.com/google/caliban#getting-started-with-caliban>`_ tutorial on
the main page of `Caliban's github repository
<https://github.com/google/caliban>`_.
