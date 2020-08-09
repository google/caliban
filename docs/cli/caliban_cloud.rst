caliban cloud
^^^^^^^^^^^^^

This command bundles your code and any other directories you specify into an
isolated Docker container and runs the resulting Python code on Google's
`AI Platform <https://cloud.google.com/ai-platform/>`_.

``caliban cloud`` supports the following arguments:

.. code-block:: text

   usage: caliban cloud [-h] [--helpfull] [--nogpu] [--cloud_key CLOUD_KEY]
                        [--extras EXTRAS] [-d DIR]
                        [--experiment_config EXPERIMENT_CONFIG] [--dry_run]
                        [--image_tag IMAGE_TAG] [--project_id PROJECT_ID]
                        [--region REGION] [--machine_type MACHINE_TYPE]
                        [--gpu_spec NUMxGPU_TYPE] [--tpu_spec NUMxTPU_TYPE]
                        [--force] [--name NAME] [-l KEY=VALUE]
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
     --image_tag IMAGE_TAG
                           Docker image tag accessible via Container Registry. If
                           supplied, Caliban will skip the build and push steps
                           and use this image tag.
     --project_id PROJECT_ID
                           ID of the GCloud AI Platform project to use for Cloud
                           job submission and image persistence. (Defaults to
                           $PROJECT_ID; errors if both the argument and
                           $PROJECT_ID are empty.)
     --region REGION       Region to use for Cloud job submission and image
                           persistence. Must be one of ['us-east4', 'us-west1',
                           'us-west2', 'us-central1', 'us-east1', 'europe-west4',
                           'europe-west1', 'europe-north1', 'asia-northeast1',
                           'asia-east1', 'asia-southeast1']. (Defaults to $REGION
                           or 'us-central1'.)
     --machine_type MACHINE_TYPE
                           Cloud machine type to request. Must be one of
                           ['n1-standard-8', 'n1-highmem-4', 'n1-highcpu-96',
                           'n1-highcpu-16', 'n1-highcpu-32', 'n1-highcpu-64',
                           'n1-standard-96', 'n1-highmem-2', 'n1-highmem-16',
                           'n1-highmem-64', 'n1-standard-32', 'n1-standard-16',
                           'n1-standard-4', 'n1-highmem-8', 'n1-highmem-96',
                           'n1-standard-64', 'n1-highmem-32', 'cloud_tpu'].
                           Defaults to 'n1-standard-8' in GPU mode, or
                           'n1-highcpu-32' if --nogpu is passed.
     --gpu_spec NUMxGPU_TYPE
                           Type and number of GPUs to use for each AI Platform
                           submission. Defaults to 1xP100 in GPU mode or None if
                           --nogpu is passed.
     --tpu_spec NUMxTPU_TYPE
                           Type and number of TPUs to request for each AI
                           Platform submission. Defaults to None.
     --force               Force past validations and submit the job as
                           specified.
     --name NAME           Set a job name for AI Platform jobs.
     -l KEY=VALUE, --label KEY=VALUE
                           Extra label k=v pair to submit to Cloud.

   pass-through arguments:
     -- YOUR_ARGS          This is a catch-all for arguments you want to pass
                           through to your script. any arguments after '--' will
                           pass through.

.. NOTE:: To use ``caliban cloud`` you'll need to make sure your machine is
   configured for Cloud access. To verify that you're set up, visit
   :doc:`../getting_started/cloud`.

Specifically, you'll need to make sure the following environment variables are
set:

* ``$PROJECT_ID``\ : The ID of the Cloud project where you'll be submitting jobs.
* ``$GOOGLE_APPLICATION_CREDENTIALS``\ : a local path to your JSON Cloud
  credentials file.

``caliban cloud`` works almost exactly like ``caliban run`` (by design!). Thanks to
Docker, the container environment available to your job on AI Platform will look
exactly like the environment available on your local machine.

This means that if you can get your job running in ``caliban local`` mode you can
be quite sure that it'll complete in Cloud as well. The advantages of Cloud mode
are:


#. The machines are much bigger
#. Multi-GPU machines, clusters and TPUs are available
#. Cloud can execute many jobs in parallel, and will pipeline jobs for you as
   jobs complete and resources become available on your project.

See the ``caliban run`` docs for a detailed walkthrough of most options available
to ``caliban cloud``.

This mode has many features explored in the "Cloud-Specific Tutorials" section
in the left-hand menu. Read on here for a description of each keyword argument
supported by ``caliban cloud``.

Arguments as Labels
~~~~~~~~~~~~~~~~~~~

As with ``caliban run``\ , any arguments you pass to your script after ``--``\ :

.. code-block:: bash

   caliban cloud trainer.train -- --epochs 2

Will be passed directly through to your script.

In cloud mode, all user arguments will be passed to cloud as labels, which means
that you can filter by these labels in the AI platform jobs UI.

Keyword Arguments
~~~~~~~~~~~~~~~~~

The additional options available to ``caliban cloud`` are:


* **image_tag**\ : If you supply the tag of a Docker image accessible from your
  project, caliban will bypass the Docker build and push steps and use this
  image tag directly for AI Platform job submission. This is useful if you want
  to submit a job quickly without going through a no-op build and push, or if
  you want to :doc:`broadcast an experiment
  <../explore/experiment_broadcasting>` using some existing container. Note that
  this flag will cause ``caliban cloud`` to ignore any ``--extras`` or ``--dir``
  arguments, as no ``docker build`` step will be executed.

* **project_id**\ : This is the ID of the Cloud project that Caliban will use to
  push Docker containers and to submit AI platform jobs. By default Caliban will
  examine your environment for a ``$PROJECT_ID`` variable; if neither is set and
  you attempt to run a Cloud command, Caliban will exit.

* **region**\ : The Cloud region you specify with this flag is used for AI
  Platform job submission. Any value listed in `AI Platform's region docs
  <https://cloud.google.com/ml-engine/docs/regions>`_ is valid. If you don't
  specify a region Caliban will examine your environment for a ``$REGION``
  variable and use this if supplied; if that's not set it will default to
  ``"us-central1"``. See ``caliban cloud --help`` for all possible arguments.

* **machine_type**\ : Specifies the type of machine to use for each submitted AI
  platform job. See ``caliban cloud --help`` for all possible values. See
  :doc:`../cloud/gpu_specs` for more detail.

* **gpu_spec**\ : optional argument of the form GPU_COUNTxGPU_TYPE. See
  ``caliban cloud --help`` for all possible GPU types, and for the default.
  Usually 1, 2, 4 or 8 of each are supported, though this depends on the machine
  type you specify. Caliban will throw a validation error and give you a
  suggestion for how to proceed if you supply a combination that's not possible
  on AI Platform. See :doc:`../cloud/gpu_specs` for more details.

* **tpu_spec**\ : optional argument of the form TPU_COUNTxTPU_TYPE. See
  ``caliban cloud --help`` for all supported TPU types. As of December 2019,
  ``8xV2`` and ``8xV3`` are the only available options. TPUs are compatible with
  GPUs specified using ``--gpu_spec``. See :doc:`../cloud/ai_platform_tpu` for
  more details.

*
  **--force**\ : If supplied, this flag will disable all validations on
  combinations of region, machine type, GPU count and GPU type and force
  caliban to submit the job to AI Platform as specified. This is useful in
  case some new GPU was added to a region or machine type and caliban hasn't
  yet been updated.

* **name**\ : If you pass a string via this optional flag, ``caliban cloud``
  will submit your job with a job id of ``"{name}_{timestamp}"`` and add a
  ``job_name:{name}`` label to your job. It's useful to pass the same name for
  MANY jobs and use this field to group various experiment runs. Experiment
  broadcasting (the next flag, keep reading!) will do this for you
  automatically.

* **experiment_config**\ : If you pass the location (relative or absolute) of a
  local JSON file of the proper format, caliban will generate many jobs using
  this experiment config and submit them all in batch to AI platform. The
  formatting rules are - keys must be strings, values can be list, int, boolean
  or string. If the value is a list, caliban will generate N copies of the
  experiment config, 1 for each entry in the list, and submit a job for each.
  The total number of jobs submitted is the cardinality of the cartesian product
  of all lists in the experiment config. Lists of valid dicts are also allowed.
  See :doc:`../explore/experiment_broadcasting` for more details.

* **label**\ : You can use this flag to pass many labels to ``caliban cloud``\ ;
  just pass the flag over and over. Labels must be of the form ``k=v``\ ;
  ``--label epochs=2``\ , for example. If you pass any labels identical to your
  flags these labels will take precedence. See :doc:`../cloud/labels` below for
  more detail.

* **dry_run**\ : this flag will force logging output of all jobs that caliban
  will submit without the ``--dry_run`` flag. Docker will also skip an actual
  build and push. Use this to check that your other arguments are well formatted
  before submitting a potentially very large batch of jobs (depending on your
  experiment config).
