caliban build
^^^^^^^^^^^^^

This command builds the Docker image used in :doc:`caliban_run`,
:doc:`caliban_cloud` and friends, without actually executing the container or
submitting it remotely.

``caliban build`` supports the following arguments:

.. code-block:: text

   usage: caliban build [-h] [--helpfull] [--nogpu] [--cloud_key CLOUD_KEY]
                        [--extras EXTRAS] [-d DIR]
                        module

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
     --no_cache            Disable Docker's caching mechanism and force a
                           rebuild of the container from scratch.
     -d DIR, --dir DIR     Extra directories to include. List these from large to
                           small to take full advantage of Docker's build cache.
