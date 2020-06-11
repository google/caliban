caliban shell
^^^^^^^^^^^^^

This command is designed for fast, iterative workflows on scripts in an
environment that's guaranteed to match the environment available to your code on
Cloud.

``caliban shell`` supports the following arguments:

.. code-block:: text

   usage: caliban shell [-h] [--helpfull] [--nogpu] [--cloud_key CLOUD_KEY]
                        [--extras EXTRAS] [--image_id IMAGE_ID]
                        [--docker_run_args DOCKER_RUN_ARGS] [--shell {bash,zsh}]
                        [--bare]

   optional arguments:
     -h, --help            show this help message and exit
     --helpfull            show full help message and exit
     --nogpu               Disable GPU mode and force CPU-only.
     --cloud_key CLOUD_KEY
                           Path to GCloud service account key. (Defaults to
                           $GOOGLE_APPLICATION_CREDENTIALS.)
     --extras EXTRAS       setup.py dependency keys.
     --image_id IMAGE_ID   Docker image ID accessible in the local Docker
                           registry. If supplied, Caliban will skip the 'docker
                           build' step and use this image.
     --docker_run_args DOCKER_RUN_ARGS
                           String of args to add to Docker.
     --shell {bash,zsh}    This argument sets the shell used inside the container
                           to one of Caliban's supported shells. Defaults to the
                           shell specified by the $SHELL environment variable, or
                           'bash' if your shell isn't supported.
     --bare                Skip mounting the $HOME directory; load a bare shell.

Running ``caliban shell`` in any directory will generate a Docker image containing
the minimal environment necessary to execute Python ML workflows and drop you
into an interactive shell inside of that image.

.. WARNING:: ``caliban shell`` is one of two modes that won't work inside of a ``piper``
   folder. You can't develop interactively, since Docker can't mount piper volumes.
   Stick to ``run``\ , ``build``\ , ``cloud`` and ``cluster`` and you'll be fine.

Caliban will copy in your Cloud credentials and set the required
``$GOOGLE_APPLICATION_CREDENTIALS`` env variable, so all Cloud interaction from
Python should Just Work. (See the :doc:`guide on gcloud authentication
<../explore/gcloud>` for more detail.)

The base Caliban images also have ``gcloud`` installed; all ``gcloud`` and ``gsutil``
commands will work with the same permissions granted to the key found at
``$GOOGLE_APPLICATION_CREDENTIALS``.

.. NOTE:: If you run ``caliban shell --bare``\ , your gcloud and gsutil will
   have the same permissions that they'll have in the cloud - the permissions
   granted by your JSON key file. If you just run ``caliban shell``\ , which
   mounts your home directory, ``gcloud`` and ``gsutil`` will preferentially
   load the config you have on your local machine.

The only python dependencies available in the container will be dependencies
that you declare explicitly in either:


* a ``requirements.txt`` file
* a ``setup.py`` file.

Your setup file can declare groups of dependencies using the setuptools
`extras_require
<https://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies>`_
feature. See the `setup.py file from our Hello Tensorflow
<https://team.git.corp.google.com/blueshift/tutorials/+/refs/heads/master/hello-tensorflow/setup.py>`_
project for an example of how to use ``extras_require`` to create separate
environments for GPU and CPU. (See the :doc:`../explore/declaring_requirements`
docs for more detail.)

By default your home directory will mount into the container, along with the
folder you're in when you run ``caliban shell``. This means that:


* your default ``bash`` (or ``zsh``\ ) environment will be available to you at the
  ``caliban shell``.
* Any changes you make to files in the mounted directory will be immediately
  available to you to run with, say, ``python -m trainer.train`` or some similar
  command.

On the Mac you'll have to pass ``--nogpu`` to ``shell``\ , as the NVIDIA runtime isn't
supported on non-Linux machines. If you forget ``caliban`` will remind you and
prevent you from getting too far.

.. NOTE:: Caliban currently supports ``bash`` and ``zsh`` shells. The command
   will use your ``$SHELL`` environment variable to pick a default; to override
   the default, you can always pass the ``--shell`` argument, like this:
   ``caliban shell --shell bash``.
