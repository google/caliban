Customizing Machines and GPUs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This section discusses the default configurations for accelerators and machine
types that Caliban requests when it submits jobs to Cloud. You'll also find
instructions on how to request different GPUs or machine types for your job.

Default GPU and Machine Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, if you don't supply ``--gpu_spec`` or ``--machine_type`` (both discussed
below), Caliban will configure your jobs on the following hardware for each
mode:


* GPU mode (default): a single P100 GPU on an ``n1-standard-8`` machine
* CPU mode: an ``n1-highcpu-32`` machine with no GPU attached

You can read more about the various machine types available on AI platform `here
<https://cloud.google.com/ml-engine/docs/machine-types>`_\ , or scan the
following sections.


Custom GPU Specs
~~~~~~~~~~~~~~~~

The optional ``--gpu_spec`` argument allows you to attach a custom number and type
of GPU to the Cloud node that will run your containerized job on AI Platform.
The required format is ``GPU_COUNTxGPU_TYPE``\ , as in this example:

.. code-block:: bash

   caliban cloud --gpu_spec 2xV100 trainer.train

This will submit your job to a node configured with 2 V100 GPUs to a machine in
the region you specify via:


* your ``$REGION`` environment variable,
* the ``--region`` CLI argument
* or, in the absence of either of those, the safe default of ``us-central1``.

When you run any ``caliban cloud`` command, the program will immediately validate
that the combination of GPU count, region, GPU type and machine type are
compatible and error quickly if they're not. If you make the impossible request
for 3 V100 GPUs:

.. code-block:: bash

   caliban cloud --gpu_spec 3xV100 trainer.train

you'll see this error message:

.. code-block::

   caliban cloud: error: argument --gpu_spec: 3 GPUs of type V100 aren't available
   for any machine type. Try one of the following counts: {1, 2, 4, 8}

   For more help, consult this page for valid combinations of GPU count, GPU type
   and machine type: https://cloud.google.com/ml-engine/docs/using-gpus

If you ask for a valid count, but a count that's not possible on the machine
type you specified - 2 V100s on an ``n1-standard-96`` machine, for example:

.. code-block:: bash

   caliban cloud --gpu_spec 2xV100 --machine_type n1-standard-96 trainer.train

You'll see this error:

.. code-block::

   'n1-standard-96' isn't a valid machine type for 2 V100 GPUs.

   Try one of these: ['n1-highcpu-16', 'n1-highmem-16', 'n1-highmem-2',
   'n1-highmem-4', 'n1-highmem-8', 'n1-standard-16', 'n1-standard-4', 'n1-standard-8']

   For more help, consult this page for valid combinations of GPU count, GPU type
   and machine type: https://cloud.google.com/ml-engine/docs/using-gpus

If you know that your combination is correct, but Caliban's internal
compatibility table hasn't been updated to support some new combination, you can
skip all of these validations by providing ``--force`` as an option.

Custom Machine Types
~~~~~~~~~~~~~~~~~~~~

The ``--machine_type`` option allows you to specify a custom node type for the
master node where your containerized job will run. ``caliban cloud --help`` will
show you all available choices.; You can also read about the various machine
types available on AI platform
`here <https://cloud.google.com/ml-engine/docs/machine-types>`_.

As an example, the following command will configure your job to run on an
``n1-highcpu-96`` instance with 8 V100 GPUs attached:

.. code-block:: bash

   caliban cloud --gpu_spec 8xV100 --machine_type n1-highcpu-96 trainer.train

As described above in :ref:`Custom GPU Specs`, ``--machine_type`` works with
``--gpu_spec`` to validate that the combination of GPU count, GPU type and
machine type are all valid, and returns an error immediately if the combination
is invalid.
