caliban run
^^^^^^^^^^^

This command bundles your code and any other directories you specify into an
isolated Docker container and runs the resulting Python code on your local
machine, but inside of the Docker environment.

``caliban run`` supports the following arguments:

.. code-block:: text

   usage: caliban run [-h] [--helpfull] [--nogpu] [--cloud_key CLOUD_KEY]
                      [--extras EXTRAS] [-d DIR]
                      [--experiment_config EXPERIMENT_CONFIG] [--dry_run]
                      [--image_id IMAGE_ID] [--docker_run_args DOCKER_RUN_ARGS]
                      module ...

   positional arguments:
     module                Code to execute, in either 'trainer.train' or
                           'trainer/train.py' format. Accepts python scripts,
                           modules or a path to an arbitrary script.

   optional arguments:
     -h, --help            show this help message and exit
     --helpfull            show full help message and exit
     --nogpu               Disable GPU mode and force CPU-only.
     --cloud_key CLOUD_KEY
                           Path to GCloud service account key. (Defaults to
                           $GOOGLE_APPLICATION_CREDENTIALS.)
     --extras EXTRAS       setup.py dependency keys.
     -d DIR, --dir DIR     Extra directories to include. List these from large to
                           small to take full advantage of Docker's build cache.
     --experiment_config EXPERIMENT_CONFIG
                           Path to an experiment config, or 'stdin' to read from
                           stdin.
     --dry_run             Don't actually submit; log everything that's going to
                           happen.
     --image_id IMAGE_ID   Docker image ID accessible in the local Docker
                           registry. If supplied, Caliban will skip the 'docker
                           build' step and use this image.
     --docker_run_args DOCKER_RUN_ARGS
                           String of args to add to Docker.

   pass-through arguments:
     -- YOUR_ARGS          This is a catch-all for arguments you want to pass
                           through to your script. any arguments after '--' will
                           pass through.

Because the container is completely isolated, to get any results from ``caliban
run`` you'll have to depend on either:


* ``stdout``\ , if you're just interested in checking if the job is running at all
  before submission to Cloud, for example, or
* Cloud buckets for persistence.

Your credentials are set up inside the container and available via the required
``$GOOGLE_APPLICATION_CREDENTIALS`` environment variable, so all Cloud access
via Python should Just Work. (See the :doc:`guide on gcloud authentication
<../explore/gcloud>` for more detail.)

The base Caliban images also have ``gcloud`` installed; all ``gcloud`` and ``gsutil``
commands will work with the same permissions granted to the key found at
``$GOOGLE_APPLICATION_CREDENTIALS``.

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


Executing a Python script
~~~~~~~~~~~~~~~~~~~~~~~~~

The most basic way to trigger a run is by passing a file path or a module name.
Any of the following will work:

.. code-block:: bash

   caliban run trainer.train -- --epochs 2
   caliban run trainer/train.py
   caliban run mycode.py
   caliban run mycode -- --learning_rates '[1,2,3]'

Any flags or commands you pass to the command after ``--`` will be passed along,
untouched, to your Python code. By configuring your job with flags you can get a
large range of behavior out of the same module.

If you specify a Python module inside of a folder, ``caliban run`` will copy only
that folder into the Docker environment. For example, if you have a
``trainer/train.py`` file and run either of the following:

.. code-block:: bash

   caliban run trainer.train
   caliban run trainer/train.py

Caliban will copy only the ``trainer`` directory into the container.

If your script lives in the root of the directory, as in the ``mycode.py`` example
above, the entire current working directory will be copied in.

This could be inefficient if your directory has lots of data you don't want, or
a folder of notebooks; if you want a smaller build image you can move your
script into a folder. Make sure to create ``__init__.py`` inside the folder to
make it a proper module.

In addition to the required module name, ``caliban run`` supports many optional
arguments. All of these must be supplied **before** the module name.

Jobs run in GPU mode by default. To toggle GPU mode off, use ``--nogpu``.

Extra Directories
~~~~~~~~~~~~~~~~~

If you want to make extra directories available inside your container, pass them
like this:

.. code-block:: bash

   caliban -d data -d models/stored trainer.train

This invocation will copy the ``data`` and ``models/stored`` directories into the
container, where they can be accessed using a relative path. All directories
must exist relative to the directory where you run ``caliban run``.
