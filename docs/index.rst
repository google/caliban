Caliban reference documentation
===================================

Caliban is a tool for developing research workflow and notebooks in an isolated
Docker environment and submitting those isolated environments to Google Compute
Cloud.

For an introduction to Caliban, start at the `Caliban GitHub page
<https://github.com/google/caliban>`_.

Overview
--------

Caliban provides five subcommands that you run inside some directory on your
laptop or workstation:

*
  `caliban shell <http://go/caliban#caliban-shell>`_ generates a Docker image
  containing any dependencies you've declared in a ``requirements.txt`` and/or
  ``setup.py`` in the directory and opens an interactive shell in that
  directory. The ``caliban shell`` environment is ~identical to the environment
  that will be available to your code when you submit it to AI Platform; the
  difference is that your current directory is live-mounted into the
  container, so you can develop interactively.

*
  ```caliban notebook`` <http://go/caliban#caliban-notebook>`_ starts a Jupyter
  notebook or lab instance inside of a docker image containing your
  dependencies; the guarantee about an environment identical to AI Platform
  applies here as well.

*
  `\ ``caliban run`` <http://go/caliban#caliban-run>`_ packages your directory's
  code into the Docker image and executes it locally using ``docker run``. If
  you have a workstation GPU, the instance will attach to it by default - no
  need to install the CUDA toolkit. The docker environment takes care of all
  that. This environment is truly identical to the AI Platform environment.
  The docker image that runs locally is the same image that will run in AI
  Platform.

*
  `\ ``caliban cloud`` <http://go/caliban#caliban-cloud>`_ allows you to submit jobs
  to AI Platform that will run inside the same docker image you used with
  ``caliban run``. You can submit hundreds of jobs at once. Any machine type,
  GPU count, and GPU type combination you specify will be validated client
  side, so you'll see an immediate error with suggestions, rather than having
  to debug by submitting jobs over and over.

*
  `\ ``caliban build`` <http://go/caliban#caliban-build>`_ builds the docker image
  used in ``caliban cloud`` and ``caliban run`` without actually running the
  container or submitting any code.

*
  `\ ``caliban cluster`` <http://go/caliban#caliban-cluster>`_ creates GKE clusters
  and submits jobs to GKE clusters.

These all work from your workstation or
`your Macbook Pro <http://go/caliban#caliban-on-macbook-pro>`_. (Yes, you can
build and submit GPU jobs to Cloud from your Mac!)

The only requirement for the directory where you run these commands is that it
declare some set of dependencies in either a ``requirements.txt`` or ``setup.py``
file. See the
`requirements section <http://go/caliban#declaring-requirements-for-caliban>`_
below for more detail.

The rest of this document contains detailed information and guides on Caliban's
various modes. If you want to get started in a more interactive way, head over
to go/bs-tutorials.

Caliban's code lives in the
`Caliban repository <http://go/caliban-code>`_.

Using Caliban
-------------

If you want to practice using Caliban with a proper getting-started style guide,
head over to go/bs-tutorials for a number of tutorials that use Caliban and AI
Platform.
`Hello Tensorflow <https://team.git.corp.google.com/blueshift/tutorials/+/refs/heads/master/hello-tensorflow/README.md>`_
is a solid place to start.

Read on for information on the specific commands exposed by Caliban.

.. toctree::
   :maxdepth: 1
   :caption: Getting Started

   getting_started/prerequisites
   getting_started/getting_caliban

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
   explore/experiment_groups

.. toctree::
   :maxdepth: 1
   :caption: Common Recipes
    experiment_groups

.. toctree::
   :maxdepth: 1
   :caption: Cloud-Specific Tutorials

.. toctree::
   :maxdepth: 1
   :caption: Caliban GKE Notes


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
