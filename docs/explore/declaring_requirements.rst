Declaring Requirements
^^^^^^^^^^^^^^^^^^^^^^

To use a Python library in your Caliban-based workflow you'll need to declare it
in either a


* ``requirements.txt`` file in the directory, or a
* ``setup.py`` file, or
* both of these together.

If you run any of the Caliban commands in a directory without these, your image
will have access to bare Python alone with no dependencies.

A ``requirements.txt`` file is the simplest way to get started. See the
`pip docs <https://pip.readthedocs.io/en/1.1/requirements.html>`_ for more
information on the structure here. You've got ``git`` inside the container, so
``git`` dependencies will work fine.

Setup.py and Extra Dependency Sets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Declaring your dependencies in a ``setup.py`` file gives you the ability to
declare different sets of dependencies for the different Caliban modes (CPU vs
GPU), in addition to your own custom dependency sets.

This solves the problem of depending on, say, ``tensorflow-gpu`` for a GPU job,
and ``tensorflow`` for normal, CPU-only jobs, without having to modify your
dependency file.

Here's an example ``setup.py`` file:

.. code-block:: python

   from setuptools import find_packages
   from setuptools import setup

   setup(
       name='hello-tensorflow',
       version='0.1',
       install_requires=['absl-py', 'google-cloud-storage'],
       extras_require={
           'cpu': ['tensorflow==2.0.*'],
           'gpu': ['tensorflow-gpu==2.0.*'],
       },
       packages=find_packages(),
       description='Hello Tensorflow setup file.')

This project has two normal dependencies - ``'absl-py'`` for flags, and
``'google-cloud-storage'`` to interact with Cloud buckets.

The ``setup.py`` file declares its Tensorflow dependencies in a dictionary under
the ``extras_require`` key. If you're using pip, you would install dependencies
from just ``install_requires`` by running

.. code-block:: bash

   pip install .

If you instead ran

.. code-block:: bash

   pip install .[gpu]

``pip`` would install


* the entries under ``install_requires``\ ,
* AND, additionally, the entries under the ``'gpu'`` key of the ``extras_require``
  dictionary.

By default, if you have a ``setup.py`` file in your directory, caliban will do the
latter and attempt to install a ``'gpu'`` set of extras, like

.. code-block::

   pip install .[gpu]

If you pass ``--nogpu`` to any of the commands, Caliban will similarly attempt to
run

.. code-block::

   pip install .[cpu]

If you don't declare these keys, don't worry. You'll see a warning that the
extras dependencies didn't exist, and everything will proceed, no problem.

If you have some other set of dependencies you want to install, you can pass
``--extras my_deps``\ , or ``-e my_deps``\ , to any of the caliban modes install those
in addition to the ``cpu`` or ``gpu`` dependency set.

You can provide many sets, like this:

.. code-block:: bash

   caliban cloud -e my_deps -e logging_extras <remaining args>

And Caliban will install the dependencies from all declared sets inside of the
containerized environment.
