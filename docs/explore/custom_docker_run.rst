Custom Docker Run Arguments
^^^^^^^^^^^^^^^^^^^^^^^^^^^

``caliban {shell, notebook, run}`` all perform some combination of ``docker build``
and ``docker run`` to provide their functionality. Each provides various sane
defaults that should be fine for most use cases; sometimes, however, you might
need to break through the ``caliban`` abstraction layer and pass arguments to
``docker run`` directly.

One example would be if you need to set environment variables inside the
container, or limit which GPUs are mounted into the container.

To pass custom options to ``docker run``\ , use ``--docker_run_args``\ , like this:

.. code-block:: bash

   caliban run --docker_run_args "--env MY_VARIABLE" trainer.train

This particular command will set ``MY_VARIABLE`` inside the container to its
current value in the shell where you run the above command, as described in the
`docker run <https://docs.docker.com/engine/reference/commandline/run/>`_
documentation. (The
`\ ``docker run`` <https://docs.docker.com/engine/reference/commandline/run/>`_ docs
have information on all possible options.)

This argument is available in ``caliban run``\ , ``caliban shell`` and ``caliban
notebook``.

You may see an error if you pass some flag or argument that ``caliban`` already
supplies. Caliban prints the ``docker run`` command it executes on each
invocation, so if you need full control you can always use ``docker run``
directly.
