caliban notebook
^^^^^^^^^^^^^^^^

This command generates the same isolated environment as the other commands, but
instead of running your code or dropping you into a shell, runs a local instance
of Jupyter based in the folder where you execute the command.

``caliban notebook`` supports the following arguments:

.. code-block:: text

   usage: caliban notebook [-h] [--helpfull] [--nogpu] [--cloud_key CLOUD_KEY]
                           [--extras EXTRAS] [--docker_run_args DOCKER_RUN_ARGS]
                           [-p PORT] [-jv JUPYTER_VERSION] [--lab] [--bare]

   optional arguments:
     -h, --help            show this help message and exit
     --helpfull            show full help message and exit
     --nogpu               Disable GPU mode and force CPU-only.
     --cloud_key CLOUD_KEY
                           Path to GCloud service account key. (Defaults to
                           $GOOGLE_APPLICATION_CREDENTIALS.)
     --extras EXTRAS       setup.py dependency keys.
     --docker_run_args DOCKER_RUN_ARGS
                           String of args to add to Docker.
     -p PORT, --port PORT  Port to use for Jupyter, inside container and locally.
     -jv JUPYTER_VERSION, --jupyter_version JUPYTER_VERSION
                           Jupyterlab version to install via pip.
     --lab                 run 'jupyter lab', vs the default 'jupyter notebook'.
     --bare                Skip mounting the $HOME directory; run an isolated
                           Jupyter lab.

By default ``caliban notebook`` runs ``jupyter notebook`` inside the container. To
run Jupyterlab, pass the ``--lab`` flag:

.. code-block:: bash

   caliban notebook --lab

As with the other commands, the only python dependencies available in the
container will be dependencies that you declare explicitly in either:


* a ``requirements.txt`` file
* a ``setup.py`` file.

Your setup file can declare groups of dependencies using the setuptools
`extras_require
<https://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies>`_
feature. (See the :doc:`../explore/declaring_requirements` docs for more detail
on how to use ``extras_require`` to create separate environments for GPU and
CPU.)

Mounted Home Directory
~~~~~~~~~~~~~~~~~~~~~~

``caliban notebook`` mounts your ``$HOME`` directory into the container, which
allows your Jupyter settings to persist across sessions. If you don't want this
for some reason, run the command with the ``--bare`` flag.

Custom Jupyer Port
~~~~~~~~~~~~~~~~~~

If you'd like to run ``notebook`` using a different port, use the ``--port`` option:

.. code-block:: bash

   caliban notebook --lab --port 8889

On the Mac you'll have to pass ``--nogpu`` to ``notebook``\ , as the NVIDIA runtime
isn't supported on non-Linux machines.
