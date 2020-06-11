dockerignore speeds up builds
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Many of Caliban's commands begin their work by triggering a ``docker build``
command; this command has a side effect of bundling up the entire directory
where you run the command into a "build context", which is zipped up and sent
off to the Docker build process on your machine.

In a directory containing machine learning code, it's not unusual that you might
also have subdirectories that contain, for example:


* large datasets that you've cached locally
* tensorboard output from local runs
* metrics

If you don't want to include any of these things in the Docker container that
caliban builds for you, you can significantly speed up your builds by creating a
file called ``.dockerignore`` in the directory of your project.

Here's an example ``.dockerignore`` file, with comments explaining each line:

.. code-block::

   # ignore the git repository info and the pip installation cache
   .git
   .cache

   # this is huge - ignore the virtualenv we've created inside the folder!
   env

   # tests don't belong inside the repo.
   tests

   # no need to package info about the packaged-up code in egg form.
   *.egg-info

   # These files are here for local development, but have nothing
   # to do with the code itself, and don't belong on the docker image.
   Makefile
   pylintrc
   setup.cfg
   __pycache__
   .coverage
   .pytest_cache

As a starting point, you might take your project's ``.gitignore`` file, copy
everything other to ``.dockerignore`` and then delete any entries that you
actually DO need inside your Docker container. An example might be some data you
don't control with ``git``\ , but that you do want to include in the container using
Caliban's ``-d`` flag.
