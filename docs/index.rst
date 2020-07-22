Caliban
=======

Caliban is a tool for developing research workflow and notebooks in an isolated
Docker environment and submitting those isolated environments to Google Compute
Cloud.

For a short tutorial introduction to Caliban, see the `GitHub page
<https://github.com/google/caliban#caliban>`_.

Overview
--------

Caliban provides five subcommands that you run inside some directory on your
laptop or workstation:

* :doc:`/cli/caliban_shell` generates a Docker image containing any dependencies
  you've declared in a ``requirements.txt`` and/or ``setup.py`` in the directory
  and opens an interactive shell in that directory. The ``caliban shell``
  environment is ~identical to the environment that will be available to your
  code when you submit it to AI Platform; the difference is that your current
  directory is live-mounted into the container, so you can develop
  interactively.

* :doc:`/cli/caliban_notebook` starts a Jupyter notebook or lab instance inside
  of a docker image containing your dependencies; the guarantee about an
  environment identical to AI Platform applies here as well.

* :doc:`/cli/caliban_run` packages your directory's code into the Docker image
  and executes it locally using ``docker run``. If you have a workstation GPU,
  the instance will attach to it by default - no need to install the CUDA
  toolkit. The docker environment takes care of all that. This environment is
  truly identical to the AI Platform environment. The docker image that runs
  locally is the same image that will run in AI Platform.

* :doc:`/cli/caliban_cloud` allows you to submit jobs to AI Platform that will
  run inside the same docker image you used with ``caliban run``. You can submit
  hundreds of jobs at once. Any machine type, GPU count, and GPU type
  combination you specify will be validated client side, so you'll see an
  immediate error with suggestions, rather than having to debug by submitting
  jobs over and over.

* :doc:`/cli/caliban_build` builds the docker image used in ``caliban cloud``
  and ``caliban run`` without actually running the container or submitting any
  code.

* :doc:`/cli/caliban_cluster` creates GKE clusters and submits jobs to GKE
  clusters.

* :doc:`/cli/caliban_status` displays information about all jobs submitted by
  Caliban, and makes it easy to interact with large groups of experiments. Use
  :doc:`/cli/caliban_status` when you need to cancel pending jobs, or re-build a
  container and resubmit a batch of experiments after fixing a bug.

These all work from :doc:`your Macbook Pro <explore/mac>`. (Yes, you can build
and submit GPU jobs to Cloud from your Mac!)

The only requirement for the directory where you run these commands is that it
declare some set of dependencies in either a ``requirements.txt`` or
``setup.py`` file. See the :doc:`requirements docs
<explore/declaring_requirements>` for more detail.

The rest of this document contains detailed information and guides on Caliban's
various modes. If you want to get started in a more interactive way, head over
to `the Caliban tutorials
directory <https://github.com/google/caliban/blob/master/tutorials/README.md>`_.

Caliban's code lives on `Github <https://github.com/google/caliban>`_.

Using Caliban
-------------

If you want to practice using Caliban with a proper getting-started style guide,
head over to `Caliban's tutorials
<https://github.com/google/caliban/blob/master/tutorials/README.md>`_ (Coming
Soon!).

See the sidebar for information on the subcommands exposed by Caliban and a
whole series of tutorials and guides that you might find interesting as you work
with Caliban.

.. toctree::
   :maxdepth: 1
   :caption: Getting Started

   getting_started/prerequisites
   getting_started/getting_caliban
   getting_started/cloud

.. toctree::
   :maxdepth: 1
   :caption: Using Caliban

   cli/caliban_shell
   cli/caliban_notebook
   cli/caliban_run
   cli/caliban_cloud
   cli/caliban_build
   cli/caliban_cluster
   cli/caliban_status
   cli/caliban_stop
   cli/caliban_resubmit
   cli/expansion

.. toctree::
   :maxdepth: 1
   :caption: Exploring Further

   explore/why_caliban
   explore/base_image
   explore/custom_docker_run
   explore/declaring_requirements
   explore/experiment_groups
   explore/calibanconfig
   explore/custom_script_args
   explore/experiment_broadcasting
   explore/exp_stdin
   explore/script_vs_module
   explore/gcloud
   explore/mac

.. toctree::
   :maxdepth: 1
   :caption: Common Recipes

   recipes/flagfile
   recipes/single_gpu
   recipes/local_dir
   recipes/dockerignore

.. toctree::
   :maxdepth: 1
   :caption: Cloud-Specific Tutorials

   cloud/labels
   cloud/gpu_specs
   cloud/ai_platform_tpu
   cloud/rate_limit
   cloud/service_account
   cloud/adc
   cloud/bucket

.. toctree::
   :maxdepth: 1
   :caption: Caliban + GKE

   gke/concepts
   gke/prereq
   gke/cluster_management
   gke/job_submission
=======
Caliban reference documentation
===================================

Composable transformations of Python+NumPy programs: differentiate, vectorize,
JIT to GPU/TPU, and more.

For an introduction to Caliban, start at the `Caliban GitHub page
<https://github.com/google/caliban>`_.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

.. argparse::
   :module: caliban.cli
   :func: caliban_parser
   :prog: caliban

.. argparse::
   :module: caliban.expansion
   :func: expansion_parser
   :prog: expansion


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
