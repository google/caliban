What can Caliban Execute?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Caliban's commands can run python files as modules or scripts. If you need more
customization, you can run arbitrary shell scripts with Caliban.

Script vs Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Inside the containerized environment, your Python script will run as a module or
a script, depending on the format of the argument you supply to caliban. If you
explicitly pass a python module, with components separated by dots:

.. code-block:: bash

   caliban cloud trainer.train -- --epochs 2 --job_dir my_directory

Your script will execute inside the container environment with the following
command:

.. code-block:: bash

   python -m trainer.train --epochs 2 --job_dir my_directory

If instead you supply a relative path to the python file, like this:

.. code-block:: bash

   caliban cloud trainer/train.py -- --epochs 2 --job_dir my_directory

Caliban will execute your code as a python *script* by passing it directly to
python without the ``-m`` flag, like this:

.. code-block:: bash

   python trainer/train.py --epochs 2 --job_dir my_directory

What does this mean for you? Concretely it means that if you execute your code
as a module, all imports inside of your script have to be declared relative to
the root directory, ie, the directory where you run the caliban command. If you
have other files inside of the ``trainer`` directory, you'll have to import them
from ``trainer/train.py`` like this:

.. code-block:: python

   import trainer.util
   from trainer.cloud import load_bucket

We do this because it enforces a common structure for all code. The reproducible
unit is the directory that holds all of the code. The script doesn't live in
isolation; it's part of a project, and depends on the other files in the code
tree as well as the dependencies declared in the root directory.

If you run your code as a script, imports will only work if they're relative to
the file itself, not to the running code.

I highly recommend running code as a module!

Using Caliban with Shell Scripts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Caliban can build containers for you that will execute arbitrary shell scripts,
in addition to python code.

If you pass a relative path that points to any file other other than:


* a python module, or
* an explicit path to a python file ending with ``.py``\ ,

to ``caliban cloud``\ , ``caliban run`` or one of the other modes that accepts
modules, caliban will execute the code as a bash script.

This feature is compatible with :doc:`custom script arguments
<custom_script_args>` or an :doc:`experiment broadcast
<experiment_broadcasting>`; your shell script will receive the same flags that
any python module would receive.
