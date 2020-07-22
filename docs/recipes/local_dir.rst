Mounting a Local Directory for Data Persistence
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's say you're using ``caliban run`` with an experiment configuration to run
many experiments locally. Because ``caliban run`` attempts to look just like the
environment you'll see in the Cloud, the command doesn't mount any local
directories by default; the container is completely isolated, and you (usually)
have to persist data by writing it to a Cloud bucket.

It's possible to avoid this, however, and use Caliban to mount a local directory
into the Docker container. If you do this, you can take advantage of local
experiment broadcasting to loop through many experimental runs on your
workstation, and still persist all results and models to your local machine.

The answer comes from the :doc:`../explore/custom_docker_run` feature. If you
pass

.. code-block:: bash

   --docker_run_args "--volume workstation_dir:/foo"

to ``caliban run``\ , Caliban will mount the directory at ``workstation_dir`` into
your container at ``/foo``. (You can use any name or directory you choose instead
of ``/foo``\ , of course.)

Let's look at an example. The following command will mount a folder called
``data`` in your workstation's home directory into your container.

.. code-block:: bash

   caliban run \
     --docker_run_args "--volume /usr/local/google/home/totoro/data:/foo"
     --experiment_config exp_config.json \
     trainer.train

When you look at ``/foo`` inside the container, you'll see all of the files on
your workstation at ``/usr/local/google/home/totoro/data``. If you create or
edit any files, those changes will happen to the files on your workstation as
well.

.. WARNING:: For some reason I don't understand, if you pass ``-v`` instead of
   ``--volume``\ , as in ``--docker_run_args "-v mydir:containerdir"``\ , the
   argument parser in Caliban will break. Use ``--volume`` and you'll be set!

If you want to play around with volume mounting, you can pass the same argument
to ``caliban shell`` to get an interactive view of the filesystem your container
will have access to when you run the above command:

.. code-block:: bash

   # "--bare" prevents your home directory from mounting.
   caliban shell --bare \
   --docker_run_args "--volume /usr/local/google/home/totoro/data:/foo"

In the shell that launches you'll see the directory mirrored:

.. code-block::

   $ caliban shell --docker_run_args "--volume /usr/local/google/home/totoro/data:/foo" --nogpu --bare
   I0122 14:30:24.923780 4445842880 docker.py:438] Running command: docker build --rm -f- /Users/totoro/code/python/tutorials/hello-tensorflow
   Sending build context to Docker daemon  36.56MB
   <....lots of Docker output....>
   Successfully built f2ba6fb7b628
   I0122 14:30:33.125234 4445842880 docker.py:666] Running command: docker run --ipc host -w /usr/app -u 735994:89939 -v /Users/totoro/code/python/tutorials/hello-tensorflow:/usr/app -it --entrypoint /bin/bash --volume /usr/local/google/home/totoro/data:/foo f2ba6fb7b628
      _________    __    ________  ___    _   __  __  __
     / ____/   |  / /   /  _/ __ )/   |  / | / /  \ \ \ \
    / /   / /| | / /    / // __  / /| | /  |/ /    \ \ \ \
   / /___/ ___ |/ /____/ // /_/ / ___ |/ /|  /     / / / /
   \____/_/  |_/_____/___/_____/_/  |_/_/ |_/     /_/ /_/

   You are running caliban shell as user with ID 735994 and group 89939,
   which should map to the ID and group for your user on the Docker host. Great!

   caliban-shell /usr/app > ls -al /foo
   total 9788
   drwx------ 21 totoro 89939     672 Jan 22 20:35  .
   drwxr-xr-x  1 root       root     4096 Jan 22 21:30  ..
   -rw-r--r--  1 totoro 89939   41689 Jan 20 21:48  sets.png
   -rw-r--r--  1 totoro 89939   82811 Jan 20 21:48  tree.png
   caliban-shell /usr/app >
