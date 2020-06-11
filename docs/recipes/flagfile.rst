Passing Flags via --flagfile
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you find yourself passing lots of flags in to some caliban subcommand, you
might consider Abseil's ``--flagfile`` feature.

.. NOTE:: `Abseil <https://abseil.io/docs/python>`_ is a Google library that we
   use to generate Caliban's CLI. You can see the options `Abseil
   <https://abseil.io/docs/python>`_ provides on top of Caliban's arguments by
   passing ``--helpfull`` to any command; ``caliban cloud --helpfull``\ , for
   example.

``--flagfile`` allows you to put any number of flags or arguments to caliban into
a file, one pair per line. Given some file like ``my_args.txt`` with the following
contents:

.. code-block::

   --docker_run_args "CUDA_VISIBLE_DEVICES=0"
   --experiment_config experiment_one.json
   --cloud_key my_key.json
   --extras extra_deps

You could run the following command:

.. code-block:: bash

   caliban run --flagfile my_args.txt trainer.train

All arguments expand in-line, so the above command would be equivalent to
running:

.. code-block:: bash

   caliban run --docker_run_args "CUDA_VISIBLE_DEVICES=0" \
               --experiment_config experiment_one.json \
               --cloud_key my_key.json \
               --extras extra_deps \
               trainer.train

One major benefit is that you can share groups of arguments between various
subcommand invocations, like ``caliban run`` and ``caliban cloud``\ , without having
to store large duplicated strings of arguments.

Nested Flagfiles
~~~~~~~~~~~~~~~~

You can supply ``--flagfile some_file`` arguments inside flag files! This allows
you to build up trees of arguments in a fine grained way. Imagine some flagfile
called ``v100_project.flags``\ :

.. code-block:: text

   # Definition for big iron GPUs.
   --gpu_spec 8xV100
   --machine_type n1-highcpu-64
   --cloud_key my_key.json

And then some further file called ``tpu_plus_gpu.flags``\ :

.. code-block:: text

   --flagfile v100_project.flags
   --tpu_spec 8xV3
   --region us-central1

The command:

.. code-block:: bash

   caliban cloud --flagfile tpu_plus_gpu.flags trainer.train

Would expand out **both** sets of flags, as expected. (I don't know what would
happen if each file referenced the other... feel free to try!)

For more information, check out the
`Abseil docs on ``--flagfile`` <https://abseil.io/docs/python/guides/flags#a-note-about---flagfile>`_.
