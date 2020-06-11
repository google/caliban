Using a Single GPU
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, ``docker run`` will make all GPUs on your workstation available
inside of the container. This means that in ``caliban shell``\ , ``caliban
notebook`` or ``caliban run``\ , any jobs executed on your workstation will
attempt to use:


* your huge GPU, custom-built and installed for ML Supremacy
* the dinky GPU that exists solely to power your monitor, NOT to help train
  models

The second GPU will slow down everything.

To stop this from happening you need to set the ``CUDA_VISIBLE_DEVICES``
environment variable equal to ``0``\ , as described on this
`nvidia blog <https://devblogs.nvidia.com/cuda-pro-tip-control-gpu-visibility-cuda_visible_devices/>`_
about the issue.

You can set the environment variable inside your container by passing
``--docker_run_args`` to caliban, like this:

.. code-block:: bash

   caliban run --docker_run_args "--env CUDA_VISIBLE_DEVICES=0" trainer.train

.. NOTE:: you may have noticed that this problem doesn't happen when you run a
   job inside ``caliban shell``. Your local environment may have
   ``CUDA_VISIBLE_DEVICES`` set. ``caliban shell`` and ``caliban notebook``
   mount your home directory by default, which loads all of your local
   environment variables into the container and, if you've set this environment
   variable, modifies this setting inside your container. This doesn't happen
   with ``caliban run`` or ``caliban cloud``. You will always need to use this
   trick with those modes.

There are two other ways to solve this problem using the
`custom ``docker run`` arguments detailed here <https://docs.docker.com/engine/reference/commandline/run/>`_.
You can directly limit the GPUs that mount into the container using the ``--gpus``
argument:

.. code-block:: bash

   caliban run --docker_run_args "--gpus device=0" trainer.train

If you run ``nvidia-smi`` in the container after passing this argument you won't
see more than 1 GPU. This is useful if you know that some library you're using
doesn't respect the ``CUDA_VISIBLE_DEVICES`` environment variable for any reason.

You could also pass this and other environment variables using an env file.
Given some file, say, ``myvars.env``\ , whose contents look like this:

.. code-block:: text

   CUDA_VISIBLE_DEVICES=0
   IS_THIS_A_VARIABLE=yes

The ``--env-file`` argument will load all of the referenced variables into the
docker environment:

.. code-block:: bash

   caliban run --docker_run_args "--env-file myvars.env" trainer.train

Check out :doc:`../explore/custom_docker_run` for more information.
