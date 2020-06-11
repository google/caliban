Caliban
=======

Caliban is a CLI tool for developing machine learning research workflows and
notebooks in an isolated Docker environment and submitting those isolated
environments to Google AI Platform. Locally, Caliban can run code against your
workstation GPU.

Caliban is completely agnostic about what code you run inside the container. You
can use Caliban to run Pytorch, Jax, Tensorflow (any version, 2.0 included) or
some custom framework on AI Platform.

Your code can live in ``g3``\ , Github, `Git-on-Borg <http://go/gob>`_ or on your
workstation or laptop; Caliban doesn't care, and works in all of these cases.

This page contains guides to Caliban's various modes and features and detailed
CLI documentation. For assistance and community beyond the text, check out these
resources:


* Internal chat: go/bs-help
* Buganizer: go/caliban-issues
* Report an issue or bug: go/caliban-bug
* Pegboard: http://p/caliban
* Code repository: go/caliban-code
* Changelog: go/caliban-changelog

Overview
--------

Caliban provides five subcommands that you run inside some directory on your
laptop or workstation:


*
  `\ ``caliban shell`` <http://go/caliban#caliban-shell>`_ generates a Docker image
  containing any dependencies you've declared in a ``requirements.txt`` and/or
  ``setup.py`` in the directory and opens an interactive shell in that
  directory. The ``caliban shell`` environment is ~identical to the environment
  that will be available to your code when you submit it to AI Platform; the
  difference is that your current directory is live-mounted into the
  container, so you can develop interactively.

*
  `\ ``caliban notebook`` <http://go/caliban#caliban-notebook>`_ starts a Jupyter
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


.. image:: https://upload.wikimedia.org/wikipedia/commons/a/ad/Stephano%2C_Trinculo_and_Caliban_dancing_from_The_Tempest_by_Johann_Heinrich_Ramberg.jpg
   :target: https://upload.wikimedia.org/wikipedia/commons/a/ad/Stephano%2C_Trinculo_and_Caliban_dancing_from_The_Tempest_by_Johann_Heinrich_Ramberg.jpg
   :alt:


..

   “Be not afeard; the isle is full of noises, Sounds, and sweet airs, that give
   delight and hurt not. Sometimes a thousand twangling instruments Will hum
   about mine ears; and sometime voices, That, if I then had waked after long
   sleep, Will make me sleep again: and then, in dreaming, The clouds methought
   would open, and show riches Ready to drop upon me; that, when I waked, I cried
   to dream again.”

   -- :raw-html-m2r:`<cite>Shakespeare, The Tempest</cite>`


Prerequisites
-------------

Before you can install and use Caliban to manage your research workflows, you'll
need a solid Cloud and Docker installation. Follow these steps to get set up.

Python 3
^^^^^^^^

Make sure your ``python3`` is up to date by running the following command at your
workstation:

.. code-block:: bash

   sudo apt-get install python3 python3-venv python3-pip

If you're on a Mac, download
`Python 3.7.5 from python.org <https://www.python.org/downloads/mac-osx>`_
(\ `direct download link <https://www.python.org/ftp/python/3.7.5/python-3.7.5-macosx10.9.pkg>`_\ )

Once that's all set, verify that you're running python 3.5 or above:

.. code-block:: bash

   $ python3 --version
   Python 3.7.5 # Or something above 3.5.3

Blueshift Internal Repo
^^^^^^^^^^^^^^^^^^^^^^^

The `Blueshift internal repository <http://go/bs-internal>`_ has some nice tooling
that will make life easier at Blueshift.

To get the Blueshift repository installed, run these three commands:

.. code-block:: bash

   git clone sso://team/blueshift/blueshift ~/dev/blueshift
   echo -e '\n#Blueshift shared aliases and functions\nsource ~/dev/blueshift/profile/bashrc' >> ~/.bashrc
   source ~/.bashrc

Please modify the above if you're using a different shell like ``zsh``.

Docker and CUDA
^^^^^^^^^^^^^^^

Caliban uses Docker for all of its tasks. To use Caliban, you'll need ``docker``
and\ ``nvidia-docker`` on your machine. Use Blueshift's
`Working with Docker <http://go/bs-docker>`_ tutorial at go/bs-docker to get
yourself set up.

If you're on a Mac laptop, just install
`Docker Desktop for Mac <http://go/bs-mac-setup>`_ (so easy!)

If you're on a workstation, you'll also need to make sure that your CUDA drivers
are up to date, and that you have a big-iron GPU installed in your workstation.

If you've installed the `Blueshift repository <http://go/bs-internal>`_ this
part's easy. Just open a new terminal window. If you don't see any warnings
about CUDA, you're set!

If you still need to install a physical GPU in your workstation, the
`Workstation GPU installation <http://go/bs-gpus>`_ tutorial at go/bs-gpus will
get you sorted.

Getting Caliban
---------------

If you've already installed the
`Blueshift internal repository <http://go/bs-internal>`_\ , the easiest way to get
Caliban is to run the following in your terminal:

.. code-block:: bash

   install_caliban

This command will install the ``caliban`` command into its own isolated virtual
environment using ``pipx``\ , and make the ``caliban`` command globally available on
your Mac or workstation.

Manual Installation
^^^^^^^^^^^^^^^^^^^

If you don't have the Blueshift repo installed, or if the above is failing, here
are the steps to get ``caliban`` on your machine, written out more exhaustively.

.. NOTE:: If you're currently in a ``virtualenv``\ , please run ``deactivate``
   to disable it before proceeding.

We'll install ``caliban`` using `\ ``pipx`` <https://pypi.org/project/pipx/>`_.
`\ ``pipx`` <https://pypi.org/project/pipx/>`_ is a tool that lets you install command
line utilities written in Python into their own virtual environments, completely
isolated from your system python packages or other virtualenvs.

You don't HAVE to do this - you can install caliban in your global environment,
or in a virtualenv - but ``pipx`` is the sanest way we've found to install Python
CLI command tools, so here goes.

Install ``pipx`` into your global python environment like this:

.. code-block:: bash

   python3 -m pip install --user pipx
   python3 -m pipx ensurepath

The next step is slightly different, depending on if you have ``pipx < 0.15.0`` or
``pipx >= 0.15.0``. Once ``pipx`` is installed, use it to install ``caliban``\ :

.. code-block:: bash

   # Command for pipx < 0.15.0
   pipx install -e --spec git+https://github.com/google/caliban.git caliban

   # Command for pipx >= 0.15.0
   pipx install git+https://github.com/google/caliban.git

Upgrading Caliban
^^^^^^^^^^^^^^^^^

With ``pipx``\ , upgrading Caliban is simple. The following command will do it:

.. code-block:: bash

   pipx upgrade caliban

Check your Installation
^^^^^^^^^^^^^^^^^^^^^^^

To check if all is well, run

.. code-block:: bash

   caliban --help

to see the list of subcommands. We'll explore the meaning of each command below.

Using Caliban
-------------

If you want to practice using Caliban with a proper getting-started style guide,
head over to go/bs-tutorials for a number of tutorials that use Caliban and AI
Platform.
`Hello Tensorflow <https://team.git.corp.google.com/blueshift/tutorials/+/refs/heads/master/hello-tensorflow/README.md>`_
is a solid place to start.

Read on for information on the specific commands exposed by Caliban.

Experiment Groups
^^^^^^^^^^^^^^^^^

Caliban supports grouping experiments into a collection called an *experiment
group*. This allows you to do things like monitor all of the jobs in a given
group, stop all running jobs in a group, or re-run all of the jobs in a group.

Each of the caliban compute backends supports specifying an experiment group via
the ``--xgroup`` flag:

.. code-block::

   $ caliban run --xgroup my-xgroup ...
   $ caliban cloud --xgroup my-xgroup ...
   $ caliban cluster job submit --xgroup my-xgroup ...

If you don't specify an experiment group when submitting jobs via caliban, a new
experiment group will be generated for you, so you don't need to use them if you
don't want to. Also, the existence of this group should be transparent to you.

You can add new jobs to an existing experiment group simply by specifying the
same group on different caliban job submission calls:

.. code-block::

   caliban cloud --xgroup my-xgroup ... foo.py --
   ...
   (some time later...)
   caliban cloud --xgroup my-xgroup ... bar.py --

The experiment group ``my-xgroup`` will contain the experiments generated by both
of the caliban calls, and you can then perform different operations on these as
described in the sections below.

``caliban status``
^^^^^^^^^^^^^^^^^^^^^^

The ``caliban status`` command allows you to check on the status of jobs submitted
via caliban. There are two primary modes for this command. The first returns
your most recent job submissions across all experiment groups:

.. code-block::

   $ caliban status --max_jobs 5
   most recent 5 jobs for user aslone:

   xgroup aslone-xgroup-2020-05-28-11-33-35:
     docker config 1: job_mode: CPU, build url: ~/sw/blueshift/caliban/tmp/cpu, extra dirs: None
      experiment id 28: cpu.py --foo 3 --sleep 2
        job 56       STOPPED        GKE 2020-05-28 11:33:35 container: gcr.io/aslone-blueshift/0f6d8a3ddbee:latest name: job-stop-test-rssqq
      experiment id 29: cpu.py --foo 3 --sleep 600
        job 57       STOPPED        GKE 2020-05-28 11:33:36 container: gcr.io/aslone-blueshift/0f6d8a3ddbee:latest name: job-stop-test-c5x6v

   xgroup aslone-xgroup-2020-05-28-11-40-52:
     docker config 1: job_mode: CPU, build url: ~/sw/blueshift/caliban/tmp/cpu, extra dirs: None
       experiment id 30: cpu.py --foo 3 --sleep -1
         job 58       STOPPED       CAIP 2020-05-28 11:40:54 container: gcr.io/aslone-blueshift/0f6d8a3ddbee:latest name: caliban_aslone_20200528_114052_1
       experiment id 31: cpu.py --foo 3 --sleep 2
         job 59       STOPPED       CAIP 2020-05-28 11:40:55 container: gcr.io/aslone-blueshift/0f6d8a3ddbee:latest name: caliban_aslone_20200528_114054_2
       experiment id 32: cpu.py --foo 3 --sleep 600
         job 60       RUNNING       CAIP 2020-05-28 11:40:56 container: gcr.io/aslone-blueshift/0f6d8a3ddbee:latest name: caliban_aslone_20200528_114055_3

Here we can see five jobs that we recently submitted, in two experiment groups.
The first experiment group has jobs submitted to GKE, while the second has jobs
submitted to CAIP. You can specify the maximum number of jobs to return using
the ``--max_jobs`` flag.

The second mode for the ``caliban status`` command returns jobs in a given
experiment group, using the ``--xgroup`` flag:

.. code-block::

   $ caliban status --xgroup xg2 --max_jobs 2
   xgroup xg2:
   docker config 1: job_mode: CPU, build url: ~/sw/blueshift/caliban/tmp/cpu, extra dirs: None
     experiment id 1: cpu.py --foo 3 --sleep -1
       job 34       FAILED        CAIP 2020-05-08 18:26:56 container: gcr.io/aslone-blueshift/e2a0b8fca1dc:latest name: caliban_aslone_1_20200508_182654
       job 37       FAILED        CAIP 2020-05-08 19:01:08 container: gcr.io/aslone-blueshift/e2a0b8fca1dc:latest name: caliban_aslone_1_20200508_190107
     experiment id 2: cpu.py --foo 3 --sleep 2
       job 30       SUCCEEDED    LOCAL 2020-05-08 09:59:04 container: e2a0b8fca1dc
       job 35       SUCCEEDED     CAIP 2020-05-08 18:26:57 container: gcr.io/aslone-blueshift/e2a0b8fca1dc:latest name: caliban_aslone_2_20200508_182656
     experiment id 5: cpu.py --foo 3 --sleep 600
       job 36       STOPPED       CAIP 2020-05-08 18:26:58 container: gcr.io/aslone-blueshift/e2a0b8fca1dc:latest name: caliban_aslone_3_20200508_182657
       job 38       SUCCEEDED     CAIP 2020-05-08 19:01:09 container: gcr.io/aslone-blueshift/e2a0b8fca1dc:latest name: caliban_aslone_3_20200508_190108

Here we can see the jobs that have been submitted as part of the ``xg2``
experiment group. By specifying ``--max_jobs 2`` in the call, we can see the two
most recent job submissions for each experiment in the group. In this case, we
can see that experiment 2 was submitted both locally and to CAIP at different
times. We can also see that experiment 1 failed (due to an invalid parameter),
and that the first submision to CAIP of experiment 5 was stopped by the user.

Another interesting thing to note here is that the container hash is the same
for each of these job submissions, so we can tell that the underlying code did
not change between submissions.

This command supports the following arguments:

.. code-block::

   $ caliban status --help
   usage: caliban status [-h] [--helpfull] [--xgroup XGROUP]
                         [--max_jobs MAX_JOBS]

   optional arguments:
     -h, --help           show this help message and exit
     --helpfull           show full help message and exit
     --xgroup XGROUP      experiment group
     --max_jobs MAX_JOBS  Maximum number of jobs to view. If you specify an
                          experiment group, then this specifies the maximum
                          number of jobs per experiment to view. If you do not
                          specify an experiment group, then this specifies the
                          total number of jobs to return, ordered by creation
                          date, or all jobs if max_jobs==0.

``caliban stop``
^^^^^^^^^^^^^^^^^^^^

This command allows you to stop running jobs submitted using caliban.

For example, suppose you submit a group of experiments to GKE using an
experiment config file like the following:

.. code-block::

   $ caliban cluster job submit --xgroup my-xgroup ... --experiment_config exp.json cpu.py --

After a bit, you realize that you made a coding error, so you'd like to stop
these jobs so that you can fix your error without wasting cloud resources (and
money). The ``caliban stop`` command makes this relatively simple:

.. code-block::

   $ caliban stop --xgroup my-xgroup
   the following jobs would be stopped:
   cpu.py --foo 3 --sleep -1
       job 61       RUNNING        GKE 2020-05-28 11:55:04 container: gcr.io/aslone-blueshift/0f6d8a3ddbee:latest name: job-stop-test-57pr9
   cpu.py --foo 3 --sleep 2
       job 62       RUNNING        GKE 2020-05-28 11:55:04 container: gcr.io/aslone-blueshift/0f6d8a3ddbee:latest name: job-stop-test-s67jt
   cpu.py --foo 3 --sleep 600
       job 63       RUNNING        GKE 2020-05-28 11:55:04 container: gcr.io/aslone-blueshift/0f6d8a3ddbee:latest name: job-stop-test-gg9zm

   do you wish to stop these 3 jobs? [yN]: y

   stopping job: 61       RUNNING        GKE 2020-05-28 11:55:04 container: gcr.io/aslone-blueshift/0f6d8a3ddbee:latest name: job-stop-test-57pr9
   stopping job: 62       RUNNING        GKE 2020-05-28 11:55:04 container: gcr.io/aslone-blueshift/0f6d8a3ddbee:latest name: job-stop-test-s67jt
   stopping job: 63       RUNNING        GKE 2020-05-28 11:55:04 container: gcr.io/aslone-blueshift/0f6d8a3ddbee:latest name: job-stop-test-gg9zm

   requested job cancellation, please be patient as it may take a short while for this status change to be reflected in the gcp dashboard or from the `caliban status` command.

This command will stop all jobs that are in a ``RUNNING`` or ``SUBMITTED`` state,
and checks with you to make sure this is what you *really* intend, as
accidentally stopping a job that has been running for days is a particularly
painful experience if your checkpointing is less than perfect. Similar to other
caliban commands, you can use the ``--dry_run`` flag to just print what jobs would
be stopped.

This command supports the following arguments:

.. code-block::

   $ caliban stop --help
   usage: caliban stop [-h] [--helpfull] [--xgroup XGROUP] [--dry_run]

   optional arguments:
     -h, --help       show this help message and exit
     --helpfull       show full help message and exit
     --xgroup XGROUP  experiment group
     --dry_run        Don't actually submit; log everything that's going to
                      happen.

``caliban resubmit``
^^^^^^^^^^^^^^^^^^^^^^^^

Often one needs to re-run an experiment after making code changes, or to run the
same code with a different random seed. Caliban supports this with its
``resubmit`` command.

This command allows you to resubmit jobs in an experiment group without having
to remember or re-enter all of the parameters for your experiments. For example,
suppose you run a set of experiments in an experiment group on CAIP:

.. code-block::

   caliban cloud --xgroup resubmit_test --nogpu --experiment_config experiment.json cpu.py -- --foo 3

You then realize that you made a coding error, causing some of your jobs to
fail:

.. code-block::

   $ caliban status --xgroup resubmit_test
   xgroup resubmit_test:
   docker config 1: job_mode: CPU, build url: ~/sw/blueshift/caliban/tmp/cpu, extra dirs: None
     experiment id 37: cpu.py --foo 3 --sleep 2
       job 69       SUCCEEDED     CAIP 2020-05-29 10:53:41 container: gcr.io/aslone-blueshift/cffd1475aaca:latest name: caliban_aslone_20200529_105340_2
     experiment id 38: cpu.py --foo 3 --sleep 1
       job 68       FAILED        CAIP 2020-05-29 10:53:40 container: gcr.io/aslone-blueshift/cffd1475aaca:latest name: caliban_aslone_20200529_105338_1

You then go and modify your code, and now you can use the ``resubmit`` command to
run the jobs that failed:

.. code-block::

   $ caliban resubmit --xgroup resubmit_test
   the following jobs would be resubmitted:
   cpu.py --foo 3 --sleep 1
     job 68       FAILED        CAIP 2020-05-29 10:53:40 container: gcr.io/aslone-blueshift/cffd1475aaca:latest name: caliban_aslone_20200529_105338_1

    do you wish to resubmit these 1 jobs? [yN]: y
   rebuilding containers...
   ...
   Submitting request!
   ...

Checking back in with ``caliban status`` shows that the code change worked, and
now all of the experiments in the group have succeeded, and you can see that the
container hash has changed for the previously failed jobs, reflecting your code
change:

.. code-block::

   $ caliban status --xgroup resubmit_test
   xgroup resubmit_test:
   docker config 1: job_mode: CPU, build url: ~/sw/blueshift/caliban/tmp/cpu, extra dirs: None
     experiment id 37: cpu.py --foo 3 --sleep 2
       job 69       SUCCEEDED     CAIP 2020-05-29 10:53:41 container: gcr.io/aslone-blueshift/cffd1475aaca:latest name: caliban_aslone_20200529_105340_2
     experiment id 38: cpu.py --foo 3 --sleep 1
       job 70       SUCCEEDED     CAIP 2020-05-29 11:03:01 container: gcr.io/aslone-blueshift/81b2087b5026:latest name: caliban_aslone_20200529_110259_1

The ``resubmit`` command supports the following arguments:

.. code-block::

   $ caliban resubmit --help
   usage: caliban resubmit [-h] [--helpfull] [--xgroup XGROUP] [--dry_run] [--all_jobs] [--project_id PROJECT_ID] [--cloud_key CLOUD_KEY]

   optional arguments:
     -h, --help            show this help message and exit
     --helpfull            show full help message and exit
     --xgroup XGROUP       experiment group
     --dry_run             Don't actually submit; log everything that's going to happen.
     --all_jobs            resubmit all jobs regardless of current state, otherwise only jobs that are in FAILED or STOPPED state will be resubmitted
     --project_id PROJECT_ID
                           ID of the GCloud AI Platform/GKE project to use for Cloud job submission and image persistence. (Defaults to $PROJECT_ID; errors if both the argument and $PROJECT_ID are empty.)
     --cloud_key CLOUD_KEY
                           Path to GCloud service account key. (Defaults to $GOOGLE_APPLICATION_CREDENTIALS.)

Troubleshooting
---------------

I can't access the Docker base image!
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Permissions! Always a pain.

If you're in the everyone@google.com group, you should be fine. If not, you're
probably trying to get an external collaborator on board. If this is the case,
write to samritchie@x.team and send him
`this link <https://pantheon.corp.google.com/storage/browser/artifacts.blueshift-playground.appspot.com?forceOnBucketsSortingFiltering=false&project=blueshift-playground>`_
and the Google account that would like access so he can get you set up.

Exploring Further
-----------------

This section contains more in-depth guide about Caliban's various features, and
how to think about what's going on when you use Caliban to interact with Docker
and AI Platform.

Why Caliban and Docker?
^^^^^^^^^^^^^^^^^^^^^^^

Caliban uses Docker to build isolated environments for your research code. What
does this mean, and why would you want to do this?

One major source of friction in machine learning research is the potential
mismatch between the environment where your code runs during local development
and the environment in AI Platform or Cloud. Here's a typical situation:


* You run your code locally against some set of dependencies you installed
  months ago in the virtual environment you use for all your code.
* You get everything working and submit it to Cloud. Minutes later you see a
  failure - your specified Tensorflow version is wrong. You submit again,
  specifying the beta of TF 2.0 that you've been using... and the job fails.
  That version's not available in Cloud.
* Finally the submission works, but the job fails again. The ``gsutil`` command
  you've been shelling out to to save your models locally isn't available on
  AI Platform.
* You sigh and look at the clock. It's 4pm. Should I have another cup of
  coffee? What am I even doing? Is this what my life has become?

Each of these issues is small, but they stack up and turn you into a broken,
cautious person, afraid to flex the wings you've forgotten are attached to your
back.

Docker is the answer to this problem. `Docker <https://www.docker.com/>`_ is a
piece of software that allows you to build and run "containers"; you can think
of a container as a tiny Linux machine that you can run on your Mac or
workstation, or ship off to execute on AI platform. The container gets access to
the resources of the machine where it's running, but can't affect that machine
in any other way.

If you design your Python code to run inside of a container, you can move that
container between different environments and know that the code's behavior won't
change.

The Trouble with Bare Docker
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To build a Docker container for your code you need to write a ``Dockerfile``. If
you try this you'll realize that you actually need many ``Dockerfile`` copies...
one for GPU mode. One for CPU mode locally. Slight tweaks show up every time you
want to add some environment variable; locally, you don't want to copy your code
into the container, since you can live-mount the directory using ``docker run``\ ,
but on AI Platform you DO need a copy.

Soon your ``Dockerfile`` is infested with comments and instructions to a future,
less patient version of yourself, even less capable of remembering all of this
than you are now.

Caliban + Docker = <3
~~~~~~~~~~~~~~~~~~~~~

If you've felt this pain, you now understand the motivation for Caliban. Caliban
is a tool that dynamically builds docker images (by dynamically generating
``Dockerfile`` instances) for the various modes you rely on for machine learning
research:


* Jupyter notebook development
* Local, interactive development at the shell
* Local execution on your workstation on GPU
* AI platform execution of 100s of jobs for some experiment

By developing your research workflows inside of Docker containers (made easy by
Caliban) you're much closer to that noble goal of reproducible research.

Theoretically, you could publish the container that Caliban builds along with
the range of experiment parameters you used to produce your data.

What's the Base Docker Image?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Caliban's modes build docker images using a dynamically generated ``Dockerfile``.
You'll see this ``Dockerfile`` stream to stdout when you run any of Caliban's
commands.

In addition to the isolation Docker provides, the images set up a Python virtual
environment inside of each container. This guarantees you a truly blank slate;
the dependencies you declare in your code directory are the only Python
libraries that will be present. No more version clashes or surprises.

Caliban uses one of two base images, depending on whether you're running in GPU
(default) or CPU mode:


* ``gcr.io/blueshift-playground/blueshift:gpu`` for the default GPU mode
* ``gcr.io/blueshift-playground/blueshift:cpu`` for CPU, or ``--nogpu``\ , mode

These are based on, respectively,


* ``tensorflow/tensorflow:2.0.0-gpu-py3``
* ``tensorflow/tensorflow:2.0.0-py3``

We chose the base Tensorflow containers only because they do the hard work of
installing all of the CUDA drivers and other software required by NVIDIA GPUs;
the virtual environment inside of the container isolates you from the installed
``tensorflow`` library. You can install any TF version you like, or use Jax or
Pytorch or any other system.

Here's a link to the
`Dockerfile <https://team.git.corp.google.com/blueshift/caliban/+/refs/heads/master/Dockerfile>`_
we use to build the two base images that sit behind all Docker images generated
by Caliban.

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

Declaring Requirements
^^^^^^^^^^^^^^^^^^^^^^

To use a Python library in your Caliban-based workflow you'll need to declare it
in either a


* ``requirements.txt`` file in the directory, or a
* ``setup.py`` file, or
* both of these together.

If you run any of the Caliban commands in a directory without these, your image
will have access to bare Python alone with no dependencies.

A ``requirements.txt`` file is the simplest way to get started. See the
`pip docs <https://pip.readthedocs.io/en/1.1/requirements.html>`_ for more
information on the structure here. You've got ``git`` inside the container, so
``git`` dependencies will work fine.

Setup.py and Extra Dependency Sets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Declaring your dependencies in a ``setup.py`` file gives you the ability to
declare different sets of dependencies for the different Caliban modes (CPU vs
GPU), in addition to your own custom dependency sets.

This solves the problem of depending on, say, ``tensorflow-gpu`` for a GPU job,
and ``tensorflow`` for normal, CPU-only jobs, without having to modify your
dependency file.

Here's an example ``setup.py`` file from the
`Hello-Tensorflow <https://team.git.corp.google.com/blueshift/tutorials/+/refs/heads/master/hello-tensorflow/README.md>`_
tutorial:

.. code-block:: python

   from setuptools import find_packages
   from setuptools import setup

   setup(
       name='hello-tensorflow',
       version='0.1',
       install_requires=['absl-py', 'google-cloud-storage'],
       extras_require={
           'cpu': ['tensorflow==2.0.*'],
           'gpu': ['tensorflow-gpu==2.0.*'],
       },
       packages=find_packages(),
       description='Hello Tensorflow setup file.')

This project has two normal dependencies - ``'absl-py'`` for flags, and
``'google-cloud-storage'`` to interact with Cloud buckets.

The ``setup.py`` file declares its Tensorflow dependencies in a dictionary under
the ``extras_require`` key. If you're using pip, you would install dependencies
from just ``install_requires`` by running

.. code-block:: bash

   pip install .

If you instead ran

.. code-block:: bash

   pip install .[gpu]

``pip`` would install


* the entries under ``install_requires``\ ,
* AND, additionally, the entries under the ``'gpu'`` key of the ``extras_require``
  dictionary.

By default, if you have a ``setup.py`` file in your directory, caliban will do the
latter and attempt to install a ``'gpu'`` set of extras, like

.. code-block::

   pip install .[gpu]

If you pass ``--nogpu`` to any of the commands, Caliban will similarly attempt to
run

.. code-block::

   pip install .[cpu]

If you don't declare these keys, don't worry. You'll see a warning that the
extras dependencies didn't exist, and everything will proceed, no problem.

If you have some other set of dependencies you want to install, you can pass
``--extras my_deps``\ , or ``-e my_deps``\ , to any of the caliban modes install those
in addition to the ``cpu`` or ``gpu`` dependency set.

You can provide many sets, like this:

.. code-block:: bash

   caliban cloud -e my_deps -e logging_extras <remaining args>

And Caliban will install the dependencies from all declared sets inside of the
containerized environment.

Custom Apt Packages
^^^^^^^^^^^^^^^^^^^

Caliban provides support for custom aptitude packages inside your container. To
require custom apt packages, create a file called ``.calibanconfig.json`` inside
your project's directory.

The ``.calibanconfig.json`` should contain a single JSON dictionary with an
``"apt_packages"`` key. The value under this key can be either a list, or a
dictionary with ``"gpu"`` and ``"cpu"'`` keys. For example, any of the following are
valid:

.. code-block:: json

   # This is a list by itself. Comments are fine, by the way.
   {
        "apt_packages": ["libsm6", "libxext6", "libxrender-dev"]
   }

This works too:

.. code-block:: json

   # You can also include a dictionary with different deps
   # for gpu and cpu modes. It's fine to leave either of these blank,
   # or not include it.
   {
       "apt_packages": {
           "gpu": ["libsm6", "libxext6", "libxrender-dev"],
           "cpu": ["some_other_package"]
       }
   }

These values will do what you expect and run ``apt-get install <package_name>``
for each package. Packages are alphabetized, so changing the order won't
invalidate Docker's build cache.

Custom Script Arguments
^^^^^^^^^^^^^^^^^^^^^^^

In ``caliban run`` or ``caliban cloud`` modes, if you pass ``--`` to the CLI, Caliban
will stop parsing commands and pass everything after ``--`` through to your
script, untouched. If you run:

.. code-block:: bash

   caliban cloud trainer.train -- --epochs 2 --job_dir my_directory

Your script will execute inside the container environment with the following
command:

.. code-block:: bash

   python -m trainer.train --epochs 2 --job_dir my_directory

This feature is compatible with
`Experiment Broadcasting <http://go/caliban#experiment-broadcasting>`_ in ``cloud``\ ,
``run`` or ``cluster`` mode; arguments are prepended to the list generated by the
specific experiment being executed from your experiment config.

Experiment Broadcasting
^^^^^^^^^^^^^^^^^^^^^^^

The ``--experiment_config`` keyword argument allows you to pass Caliban a config
that can run many instances of your containerized job by passing each job a
different combination of some set of parameters. These parameters are passed to
your job as ``--key value`` style flags that you can parse with
`\ ``abseil`` <https://abseil.io/docs/python/quickstart>`_ or
`\ ``argparse`` <https://docs.python.org/3/library/argparse.html>`_.

This keyword is accepted by the following subcommands:


* ``caliban cloud``\ , to submit experiments to AI Platform
* ``caliban run`` to run experiments in sequence on a local workstation
* ``caliban cluster`` to execute experiments on a GKE cluster

The documentation below will refer to ``caliban cloud``\ , but all commands will
work just as well with these other modes unless explicitly called out otherwise.

``--experiment_config`` accepts a path, local or absolute, to a JSON file on your
local machine. That JSON file defines a sweep of parameters that you'd like to
explore in an experiment. Let's look at the format, and what it means for job
submission.

Experiment.json Format
~~~~~~~~~~~~~~~~~~~~~~

You can name the file whatever you like, but we'll refer to it here as
``experiment.json`` always. Here's an example ``experiment.json`` file:

.. code-block:: json

   {
       # comments work inside the JSON file!
       "epochs": [2, 3],
       "batch_size": [64, 128], # end of line comments too.
       "constant_arg": "something"
       "important_toggle": [true, false]
   }

The following command will submit an experiment using the above experiment
definition:

.. code-block:: bash

   caliban cloud --experiment_config ~/path/to/experiment.json trainer.train

For this particular ``experiment.json`` file, Caliban will submit 8 different jobs
to AI Platform with the following combinations of flags, one combination for
each job:

.. code-block:: bash

   --epochs 2 --batch_size 64 --constant_arg 'something' --important_toggle
   --epochs 2 --batch_size 64 --constant_arg 'something'
   --epochs 2 --batch_size 128 --constant_arg 'something' --important_toggle
   --epochs 2 --batch_size 128 --constant_arg 'something'
   --epochs 3 --batch_size 64 --constant_arg 'something' --important_toggle
   --epochs 3 --batch_size 64 --constant_arg 'something'
   --epochs 3 --batch_size 128 --constant_arg 'something' --important_toggle
   --epochs 3 --batch_size 128 --constant_arg 'something'

As you can see, keys get expanded out into ``--key`` style flags by prepending a
``--`` onto the key string. Here are the rules for value expansion:


* ``int`` and ``string`` values are passed on to every job untouched.
* lists generate multiple jobs. ``caliban cloud`` takes the cartesian product of
  all list-type values and generates a job for each combination. Three lists
  of length 2 in the above example gives us 8 total jobs; one for each
  possible combination of items from each list.
* if a value equals ``true``\ , the key is passed through as ``--key``\ , with no
  value; it's treated as a boolean flag.
* a ``false`` boolean value means that the ``--key`` flag is ignored.

All arguments generated from the experiment config will create labels in the AI
Platform Job UI for each job as described in the
`job labels <http://go/caliban#job-labels>`_ section.

Any `custom script arguments <http://go/caliban#custom-script-arguments>`_ you
pass after the module name, separated by ``--``\ , will be passed along to every job
as if they were static key-value pairs in the ``experiment.json`` file. As an
example, the following command:

.. code-block:: bash

   caliban cloud --experiment_config ~/path/to/experiment.json trainer.train -- --key value

would trigger the same jobs as before, with ``--key value`` appended BEFORE the
arguments broadcast out by the experiment config:

.. code-block:: bash

   --key value --epochs 2 --batch_size 64 --constant_arg 'something' --important_toggle
   --key value --epochs 2 --batch_size 64 --constant_arg 'something'
   # ....etc

Lists of Experiment Definitions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can pass either an experiment config or a LIST of experiment configs in your
``experiment.json`` file; caliban will expand each entry in the list recursively.
This makes it possible to generate experiment configs that aren't strict
cartesian products.

For example you might add the following to a file called ``experiment.json``\ , and
pass it to your job with ``--experiment_config experiment.json``\ :

.. code-block:: json

   [
       {
           "epochs": [1,2, 3, 4],
           "batch_size": [64, 128],
           "constant_arg": "something",
           "important_toggle": [true, false]
       },
       {
           "epochs": [9, 10],
           "batch_size": [512, 1024],
           "constant_arg": "something"
       }
       {
           "epochs": 1000,
           "batch_size": 1
       }
   ]

This config will generate:


* 16 combinations for the first dictionary (every combination of 4 epoch
  entries, 2 batch sizes, and 2 ``"important_toggle"`` combos, with
  ``"constant_arg"`` appended to each)
* 4 combos for the second dictionary
* 1 static combo for the third entry.

for a total of 21 jobs. You can always pass ``--dry_run`` (see below) to ``caliban
cloud`` to see what jobs will be generated for some experiment config, or to
validate that it's well-formed at all.

Compound keys
~~~~~~~~~~~~~

By default, an experiment specification in which multiple values are lists will
be expanded using a Cartesian product, as described above. If you want multiple
arguments to vary in concert, you can use a compound key. For example, the
following (w/o compound keys) experiment config file will result in four jobs
total:

.. code-block:: json

   {
     "a": ["a1", "a2"],
     "b": ["b1", "b2"]
   }

Results in:

.. code-block:: bash

   --a a1 --b b1
   --a a1 --b b2
   --a a2 --b b1
   --a a2 --b b2

To tie the values of ``a`` and ``b`` together, specify them in a compound key:

.. code-block:: json

   {
     "[a,b]": [["a1", "b1"], ["a2", "b2"]]
   }

This will result in only two jobs: ``bash --a a1 --b b1 --a a2 --b b2``

``--dry_run``
~~~~~~~~~~~~~~~~~

Passing an ``--experiment_config`` to ``caliban cloud`` could potentially submit
many, many jobs. To verify that you have no errors and are submitting the number
of jobs you expect, you can add the ``--dry_run`` flag to your command, like this:

.. code-block:: bash

   caliban cloud --dry_run --experiment_config ~/path/to/experiment.json trainer.train

``--dry_run`` will trigger all of the logging side effects you'd see on job
submission, so you can verify that all of your settings are correct. This
command will skip any docker build and push phases, so it will return
immediately with no side effects other than logging.

Once you're sure that your jobs look good and you pass all validations, you can
remove ``--dry_run`` to submit all jobs.

Experiments and Custom Machine + GPUs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you supply a ``--gpu_spec`` or ``--machine_type`` in addition to
``--experiment_config``\ , every job in the experiment submission will be configured
with those options.

Experiment Config via stdin, pipes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In addition to passing an explicit JSON file to ``caliban cloud
--experiment_config``\ , if you pass the string ``stdin`` as the flag's value
``caliban cloud`` will attempt to read the experiment config in off of ``stdin``.

As an example, this command pipes in a config and also passes ``--dry_run`` to
show the series of jobs that WILL be submitted when the ``--dry_run`` flag is
removed:

.. code-block:: bash

   cat experiment.json | caliban cloud --experiment_config stdin --dry_run trainer.train

Because ``experiment.json`` is a file on disk, the above command is not that
interesting, and equivalent to running:

.. code-block:: bash

   caliban cloud --experiment_config experiment.json --dry_run trainer.train

Things get more interesting when you need to dynamically generate an experiment
config.

Imagine you've written some python script ``generate_config.py`` that builds up a
list of complex, interdependent experiments. If you modify that script to print
a ``json`` list of ``json`` dicts when executed, you can pipe the results of the
script directly into ``caliban cloud``\ :

.. code-block:: bash

   python generate_config.py --turing_award 'winning' | \
     caliban cloud --experiment_config stdin --dry_run trainer.train

And see immediately (thanks to ``--dry_run``\ ) the list of jobs that would be
executed on AI Platform with a real run.

Experiment File Expansion and Pipes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `\ ``expansion`` <http://go/caliban#expansion>`_ command described
`above <http://go/caliban#expansion>`_ allows you to expand an experiment config
into its component JSON objects. Because these are printed to ``stdout``\ , you can
pipe them directly in to Caliban's commands, like this:

.. code-block:: bash

   expansion experiment.json | caliban cloud --experiment_config stdin trainer.train

You can also insert your own script into the middle of this pipeline. Imagine a
script called ``my_script.py`` that:


* reads a JSON list of experiments in via ``stdin``
* modifies each entry by inserting a new key whose value is a function of one
  or more existing entries
* prints the resulting JSON list back out to ``stdout``

You could sequence these steps together like so:

.. code-block:: bash

   cat experiment.json | \
     expansion experiment.json | \
     my_script.py | \
     caliban cloud --experiment_config stdin --dry_run trainer.train

If you supply ``--dry_run`` to caliban, as in the example above, caliban will
print out all of the jobs that this particular command will kick off when you
remove ``--dry_run``. This is a great way to generate complex experiments and test
everything out before submitting your jobs.

Python Execution - Script vs Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Inside the containerized environment, your Python script will run as a module or
a script, depending on the format of the argument you supply to caliban. If you
explicitly pass a python module, with components separated by dots:

.. code-block:: bash

   caliban cloud trainer.train -- --epochs 2 --job_dir my_directory

Your script will execute inside the container environment with the following
command:

.. code-block:: bash

   python -m trainer.train --epochs 2 --job_dir my_directory

If instead you supply a relative path to the python file, like this:

.. code-block:: bash

   caliban cloud trainer/train.py -- --epochs 2 --job_dir my_directory

Caliban will execute your code as a python *script* by passing it directly to
python without the ``-m`` flag, like this:

.. code-block:: bash

   python trainer/train.py --epochs 2 --job_dir my_directory

What does this mean for you? Concretely it means that if you execute your code
as a module, all imports inside of your script have to be declared relative to
the root directory, ie, the directory where you run the caliban command. If you
have other files inside of the ``trainer`` directory, you'll have to import them
from ``trainer/train.py`` like this:

.. code-block:: python

   import trainer.util
   from trainer.cloud import load_bucket

We do this because it enforces a common structure for all code. The reproducible
unit is the directory that holds all of the code. The script doesn't live in
isolation; it's part of a project, and depends on the other files in the code
tree as well as the dependencies declared in the root directory.

If you run your code as a script, imports will only work if they're relative to
the file itself, not to the running code.

I highly recommend running code as a module!

Using Caliban with Shell Scripts
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Caliban can build containers for you that will execute arbitrary shell scripts,
in addition to python code.

If you pass a relative path that points to any file other other than:


* a python module, or
* an explicit path to a python file ending with ``.py``\ ,

to ``caliban cloud``\ , ``caliban run`` or one of the other modes that accepts
modules, caliban will execute the code as a bash script.

This feature is compatible with
`custom script arguments <http://go/caliban#custom-script-arguments>`_ or an
`experiment broadcast <http://go/caliban#experiment-broadcasting>`_\ ; your shell
script will receive the same flags that any python module would receive.

GCloud and GSUtil Authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Caliban supports authentication with GCloud and GSUtil via two methods:


* `Service Account Keys <https://cloud.google.com/iam/docs/creating-managing-service-account-keys>`_\ ,
  and
* `Application Default Credentials <https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login>`_

Service accounts keys (described on Blueshift's
`Setting Up Cloud page <http://go/bs-cloud#service-account-key>`_\ ) are the method
of authentication you'll find recommended by most Cloud documentation for
authentication within Docker containers.

Unfortunately, newer GCP projects created internally at Google are all housed
inside an "experimental" folder that's banned creation of service account keys.
For those projects, you'll need to use a different method of authentication
called "Application Default Credentials", or ADC.

.. NOTE:: to set up service account keys, visit the `Blueshift service account
   instructions <http://go/bs-cloud#service-account-key>`_. To generate
   application default credentials on your machine, simply run ``gcloud auth
   application-default login`` at your terminal, as described `in the Cloud docs
   <https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login>`_.

If you've logged to gcloud on your machine using application default
credentials, Caliban will copy your stored ADC credentials into your container.
If you DON'T have a service account, gcloud and the cloud python SDK will use
these ADC credentials inside the container and work just as they do on your
workstation.

If you've followed the service account key instructions above and declared a
``GOOGLE_APPLICATION_CREDENTIALS`` environment variable on your system pointing to
a Cloud JSON service account key, Caliban will copy that key into the container
that it builds and set up an environment variable in the container pointing to
the key copy.

You can set or override this variable for a specific caliban command by
supplying ``--cloud_key ~/path/to/my_key.json``\ , like so:

.. code-block:: bash

   caliban run --cloud_key ~/path/to/my_key.json trainer.train

.. WARNING:: If you supply this option to ``caliban shell`` or ``caliban
   notebook`` and have ``GOOGLE_APPLICATION_CREDENTIALS`` set in your
   ``.bashrc``, that variable will overwrite the key that the ``--cloud_key``
   option pushes into your container. To get around this, pass ``--bare`` to
   ``caliban shell`` or ``caliban notebook`` to prevent your home directory from
   mounting and, by extension, any of your environment variables from
   overwriting the environment variable set inside the container.

The environment variable and/or option aren't necessary, but if you don't have
either of them AND you don't have ADC credentials on your machine, you won't be
able to use the GCloud Python API or the ``gsutil`` or ``gcloud`` commands inside
the container.

As noted above, if you don't have this variable set up yet and want to get it
working, check out the
`Blueshift service account instructions <http://go/bs-cloud#service-account-key>`_.
To generate application default credentials on your machine, simply run ``gcloud
auth application-default login`` at your terminal, as described
`in the Cloud docs <https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login>`_.

GCloud SDK
~~~~~~~~~~

The `GCloud SDK <https://cloud.google.com/sdk/>`_ (\ ``gsutil``\ , ``gcloud`` and friends)
is also available inside of the containerized environment.

On your local machine, ``gsutil`` and ``gcloud`` are authorized using your Google
credentials and have full administrative access to anything in your project.
Inside of the container, these tools are authenticated using the JSON service
account key; this means that if your service account key is missing permissions,
you may see a mismatch in behavior inside the container vs on your workstation.

Shell Mode Caveats
~~~~~~~~~~~~~~~~~~

``caliban shell`` introduces one potentially confusing behavior with these Cloud
credentials. By default, ``caliban shell`` will mount your home directory inside
the container; it does this so that you have all of your bash aliases and your
familiar environment inside of the container. (You can disable this with the
``--bare`` option by running ``caliban shell --bare``\ ).

Mounting your ``$HOME`` directory will trigger an evaluation of your
``$HOME/.bashrc`` file, which will ``export GOOGLE_APPLICATION_CREDENTIALS`` and
overwrite the service key variable that Caliban has set up inside of the
container.

If you use a relative path for this variable on your workstation, like:

.. code-block:: bash

   export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/devkey.json"

then everything will still work out wonderfully; inside of the container,
``$HOME`` will resolve to the in-container ``$HOME``\ , but because everything on your
workstation's ``$HOME`` is mounted the container environment will find the key.

If, instead, you use an absolute path, like:

.. code-block:: bash

   export GOOGLE_APPLICATION_CREDENTIALS="/usr/local/google/home/totoro/.config/devkey.json"

The key won't resolve inside the container. (This only applies in ``caliban
shell`` and ``caliban notebook``\ , not in ``caliban {cloud,run}``.)

To fix this, just change your absolute path to a relative path and everything
will work as expected:

.. code-block:: bash

   export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/devkey.json"

Caliban on Macbook Pro
^^^^^^^^^^^^^^^^^^^^^^

If you're developing on your Macbook, you'll be able to build GPU containers,
but you won't be able to run them locally. You can still submit GPU jobs to AI
Platform!

To use Caliban's ``shell``\ , ``notebook`` and ``run``\ , you'll have to pass ``--nogpu`` as
a keyword argument. If you don't do this you'll see the following error:

.. code-block:: bash

   [totoro@totoro-macbookpro hello-tensorflow (master)]$ caliban run trainer.train

   'caliban run' doesn't support GPU usage on Macs! Please pass --nogpu to use this command.

   (GPU mode is fine for 'caliban cloud' from a Mac; just nothing that runs locally.)

The `prerequisites <http://go/caliban#prerequisites>`_ section above covers
Macbook installation of Docker and other dependencies.

Common Recipes
--------------

This section contains descriptions of various common, application specific
patterns that users have found helpful when working with Caliban.

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

.. code-block:: txt

   # Definition for big iron GPUs.
   --gpu_spec 8xV100
   --machine_type n1-highcpu-64
   --cloud_key my_key.json

And then some further file called ``tpu_plus_gpu.flags``\ :

.. code-block:: txt

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

Using a Single GPU on a Workstation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, ``docker run`` will make all GPUs on your workstation available inside
of the container. This means that in ``caliban shell``\ , ``caliban notebook`` or
``caliban run``\ , any jobs executed on your workstation will attempt to use:


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
   job inside ``caliban shell``. If you've installed the `Blueshift internal
   repo <http://go/bs-internal>`_\ , your local environment has
   ``CUDA_VISIBLE_DEVICES`` set (\ `see here
   <https://team.git.corp.google.com/blueshift/blueshift/+/refs/heads/master/profile/bashrc#291>`_
   for the code where this happens). ``caliban shell`` and ``caliban notebook``
   mount your home directory by default, which loads all of your local
   environment variables into the container. You will always need to use this
   trick with ``caliban run``.

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

.. code-block:: txt

   CUDA_VISIBLE_DEVICES=0
   IS_THIS_A_VARIABLE=yes

The ``--env-file`` argument will load all of the referenced variables into the
docker environment:

.. code-block:: bash

   caliban run --docker_run_args "--env-file myvars.env" trainer.train

Check out this document's
`Custom Docker Run Arguments <http://go/caliban#custom-docker-run-arguments>`_
section for more information.

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

The answer comes from the
`custom ``docker run`` arguments <http://go/caliban#custom-docker-run-arguments>`_
feature. If you pass

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
     / ____/   |  / /   /  _/ __ )/   |  / | / /  \ \
    / /   / /| | / /    / // __  / /| | /  |/ /    \ \
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

Here's an example ``.dockerignore`` file from one of our tutorial projects at
go/bs-tutorials, with comments explaining each line

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

Cloud Specific Tutorials
------------------------

These tutorials cover advanced features that are only available when submitting
jobs to Cloud. Read on to gain glorious AI Platform abilities.

Job Labels
^^^^^^^^^^

AI Platform provides you with the ability to label your jobs with key-value
pairs. Any arguments you provide using either
`custom script arguments <http://go/caliban#custom-script-arguments>`_ or an
`experiment broadcast <http://go/caliban#experiment-broadcasting>`_ will be added
to your job as labels, like this:


.. image:: https://screenshot.googleplex.com/R0hHH5a12Ad.png
   :target: https://screenshot.googleplex.com/R0hHH5a12Ad.png
   :alt: Job labels


In addition to arguments Caliban will add these labels to each job:


* **\ ``job_name``\ **\ : ``caliban_totoro`` by default, or the argument you pass
  using ``caliban cloud --name custom_name``
* **\ ``gpu_enabled``\ **\ : ``true`` by default, or ``false`` if you ran your job with
  ``--nogpu``

Cloud has fairly strict requirements on the format of each label's key and
value; Caliban will transform your arguments into labels with the proper
formatting, so you don't have to think about these.

Additional Custom Labels
~~~~~~~~~~~~~~~~~~~~~~~~

You can also pass extra custom labels using ``-l`` or ``--label``\ :

.. code-block:: bash

   caliban cloud -l key:value --label another_k:my_value ...

These labels will be applied to every job if you're running an
`experiment broadcast <http://go/caliban#experiment-broadcasting>`_\ , or to the
single job you're submitting otherwise.

If you provide a label that conflicts with a user argument or experiment flag,
your label will get knocked out.

.. NOTE:: periods aren't allowed in labels, but are often quite meaningful;
   because of this caliban replaces periods with underscores before stripping
   out any restricted characters.

Default GPU and Machine Types
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

By default, if you don't supply ``--gpu_spec`` or ``--machine_type`` (both discussed
below), Caliban will configure your jobs on the following hardware for each
mode:


* GPU mode (default): a single P100 GPU on an ``n1-standard-8`` machine
* CPU mode: an ``n1-highcpu-32`` machine with no GPU attached

You can read more about the various machine types available on AI platform
`here <https://cloud.google.com/ml-engine/docs/machine-types>`_\ , or scan the
`Custom GPU Specs <http://go/caliban#custom-gpu-specs>`_ and
`Custom Machine Types <http://go/caliban#custom-machine-types>`_ sections below.

Custom GPU Specs
^^^^^^^^^^^^^^^^

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

TPUs on AI Platform
^^^^^^^^^^^^^^^^^^^

.. NOTE:: This documentation is currently quite sparse; expect a tutorial in the
   `tutorials repository <http://go/bs-tutorials>`_ soon.

.. IMPORTANT:: Unlike on Cloud, TPUs on AI Platform only support (as of
   Dec 2019) Tensorflow versions 1.13 and 1.14. No Jax, no Pytorch.

Caliban has Tensorflow version 2.1 hardcoded internally. Once the range of
possible values expands we'll make this customizable.

See `AI Platform's runtime version list
<https://cloud.google.com/ml-engine/docs/runtime-version-list>`_ for more
detail.


If you supply the ``--tpu_spec NUM_TPUSxTPU_TYPE`` argument to your ``caliban
cloud`` job, AI Platform will configure a worker node with that number of TPUs
and attach it to the master node where your code runs.

``--tpu_spec`` is compatible with ``--gpu_spec``\ ; the latter configures the master
node where your code lives, while the former sets up a separate worker instance.

CPU mode by Default
~~~~~~~~~~~~~~~~~~~

Normally, all jobs default to GPU mode unless you supply ``--nogpu`` explicitly.
This default flips when you supply a ``--tpu_spec`` and no explicit ``--gpu_spec``.
In that case, ``caliban cloud`` will NOT attach a default GPU to your master
instance. You have to ask for it explicitly.

A CPU mode default also means that by default Caliban will try to install the
``'cpu'`` extra dependency set in your ``setup.py``\ , as described in the
`Declaring Requirements <http://go/caliban#declaring-requirements>`_ guide above.

Authorizing TPU Access
~~~~~~~~~~~~~~~~~~~~~~

Before you can pass ``--tpu_spec`` to a job you'll need to authorize your Cloud
TPU to access your service account. If you have the
`Blueshift internal repo <http://go/bs-internal>`_ installed, this is as easy as
running:

.. code-block:: bash

   activate_tpu_service_account

Otherwise check out
`the AI Platform TPU tutorial <https://cloud.google.com/ml-engine/docs/tensorflow/using-tpus#authorize-tpu>`_
for more detailed steps.

Example Workflows
~~~~~~~~~~~~~~~~~

Next you'll need to get the repository of TPU examples on your machine.

.. code-block:: bash

   mkdir tpu-demos && cd tpu-demos
   curl https://codeload.github.com/tensorflow/tpu/tar.gz/r1.14 -o r1.14.tar.gz
   tar -xzvf r1.14.tar.gz && rm r1.14.tar.gz

Check out the
`AI Platform TPU tutorial <https://cloud.google.com/ml-engine/docs/tensorflow/using-tpus#authorize-tpu>`_
for the next steps, and check back for more detail about how to use that
tutorial with Caliban.

Custom Machine Types
^^^^^^^^^^^^^^^^^^^^

The ``--machine_type`` option allows you to specify a custom node type for the
master node where your containerized job will run. ``caliban cloud --help`` will
show you all available choices.; You can also read about the various machine
types available on AI platform
`here <https://cloud.google.com/ml-engine/docs/machine-types>`_.

As an example, the following command will configure your job to run on an
``n1-highcpu-96`` instance with 8 V100 GPUs attached:

.. code-block:: bash

   caliban cloud --gpu_spec 8xV100 --machine_type n1-highcpu-96 trainer.train

As described above in `Custom GPU Specs <http://go/caliban#custom-gpu-specs>`_\ ,
``--machine_type`` works with ``--gpu_spec`` to validate that the combination of GPU
count, GPU type and machine type are all valid, and returns an error immediately
if the combination is invalid.

Rate Limiting
^^^^^^^^^^^^^

``caliban cloud`` relies on AI Platform for rate limiting, so you can submit many,
many jobs using an ``--experiment_config`` (up to ~1500 total, I believe?) and AI
Platform will throttle submissions to the default limit of 60 submissions per
minute. If your project's been granted higher quotas, you won't be throttled
until you hit your project's rate limit.

Job submission on Cloud presents a nice progress bar, with terminal colors and
more. The log commands, URLs, jobIds and custom arguments are highlighted so
it's clear which jobs are going through. On a failure the error message prints
in red.


.. image:: https://screenshot.googleplex.com/ucAYKrE7Dro.png
   :target: https://screenshot.googleplex.com/ucAYKrE7Dro.png
   :alt: progress bar


What's Missing/Coming Next?
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Here are our thoughts on where this project might go next. Let me know at
`samritchie@google.com <mailto:samritchie@google.com>`_ if any of these features
are essential, or if you'd love to see them in a future version.

.. NOTE:: You can also look at our buganizer component's list of issues over at
   go/caliban-issues. Feel free to report any bugs or feature requests at
   go/caliban-bug.

Parameter Servers
~~~~~~~~~~~~~~~~~

We haven't wired in support for parameter servers yet; we're not using this
feature on Blueshift, but let us know (samritchie@google.com) and we can
prioritize this.

Custom Base Image
~~~~~~~~~~~~~~~~~

The base image is usable but it could be smaller; you also might want to build
on our default base images to install other CLI tooling and libraries.

**\ ``caliban export``\ **
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This subcommand will export a ``Dockerfile`` and all code that would have been
copied into the container by ``caliban cloud`` or ``caliban run`` into its own
directory, along with a ``README.md`` containing the commands required to build
and run the image without caliban.

You can use the exported directory as a starting point for the open source
repository that backs your research without requiring other researchers to have
Caliban installed to regenerate your Docker image.

Caliban Cluster Notes and Use Case Examples
-------------------------------------------

Here are some common caliban/GKE use cases with some notes about typical
behaviors and useful debugging and monitoring tools, along with some general GKE
concepts and information.

GKE Concepts
^^^^^^^^^^^^

Caliban makes it easy to create your own GKE Cluster - similar to your own
personal copy of AI Platform - in your Cloud project, and submit jobs to that
cluster. The advantage over AI Platform currently is that you can get more
quota, often 10x what you have available in AI Platform, and many features are
supported in GKE much earlier than they are in AI Platform.

The quota disparity is particularly notable with TPUs. AI Platform currently
only allows 8 TPUs, while a GKE cluster lets you specify 32, 64, etc TPUs for a
given job.

A good collection of GKE documentation can be found
`here <https://cloud.google.com/kubernetes-engine/docs/concepts>`_

Cluster
~~~~~~~

A
`cluster <https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-architecture>`_
is a collection of cloud machines, combining a set of *nodes* that run your
processing jobs, and *control plane* (also referred to as a *cluster master*\ )
that manages these worker nodes and handles scheduling your jobs and creating
worker nodes to run them.

Cluster Master
~~~~~~~~~~~~~~

A
`cluster master <https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-architecture#master>`_
is the controller for the cluster and all its resources. It handles creating and
deleting worker nodes, and scheduling jobs submitted by users.

Nodes
~~~~~

A
`node <https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-architecture#nodes>`_
is a worker machine (a cloud compute engine instance) that actually performs the
work your job requires. The cluster control plane creates and manages these
instances.

Node Pool
~~~~~~~~~

A
`node pool <https://cloud.google.com/kubernetes-engine/docs/concepts/node-pools>`_
is a collection of identical nodes (cpu, memory, gpu, tpu).

Job
~~~

A
`job <https://cloud.google.com/kubernetes-engine/docs/concepts/batch-reference#batchjobs>`_
is a task that is to be run to completion using cluster resources. The cluster
control plane manages the resources the job needs and handles restarting the job
in case of failure or preemption. A job probably matches the concept you have in
mind when you think of a job you submit to AI platform. A job is a top-level
task, which may be run on multiple machines/containers, which in GKE are
referred to as *pods*\ , described below.

Pod
~~~

A `pod <https://cloud.google.com/kubernetes-engine/docs/concepts/pod>`_ is a
single, ephemeral, running execution of your container. A job may run on several
pods.

GKE Prerequisites
^^^^^^^^^^^^^^^^^

There are a few prerequisites for creating and submitting jobs to a gke cluster.

Required Permissions
~~~~~~~~~~~~~~~~~~~~

To create and use a GKE cluster, you'll need to modify your service account key
to give it Account Owner permissions. Those instructions live here:
http://go/bs-cloud#modifying-service-account-permissions. Note that this only
applies if you are using a service account key.

Cluster Creation
^^^^^^^^^^^^^^^^

As described earlier in
`the section on cluster creation <http://go/caliban#caliban-cluster-create>`_\ , you
will typically create a cluster once for a given project and leave it running.

You can create a cluster for your project as follows:

.. code-block:: bash

   aslone@aslone:$ caliban cluster create --cluster_name blueshift --zone us-central1-a
   I0204 09:24:08.710866 139910209476416 cli.py:165] creating cluster blueshift in project aslone-blueshift in us-central1-a...
   I0204 09:24:08.711183 139910209476416 cli.py:166] please be patient, this may take several minutes
   I0204 09:24:08.711309 139910209476416 cli.py:167] visit https://pantheon.corp.google.com/kubernetes/clusters/details/us-central1-a/blueshift?project=aslone-blueshift to monitor cluster creation progress
   I0204 09:28:05.274621 139910209476416 cluster.py:1091] created cluster blueshift successfully
   I0204 09:28:05.274888 139910209476416 cluster.py:1092] applying nvidia driver daemonset...

The command will typically take several minutes to complete. The command will
provide you with an url you can follow to monitor the creation process. The page
will look something like the following:


.. image:: https://screenshot.googleplex.com/bhtqhet5Xu3.png
   :target: https://screenshot.googleplex.com/bhtqhet5Xu3.png
   :alt: cluster creation progress


Once your cluster is created and running, you can view and inspect it from the
cloud dashboard from the ``Kuberenetes Engine > Clusters`` menu option:


.. image:: https://screenshot.googleplex.com/5mJEi29VPjH.png
   :target: https://screenshot.googleplex.com/5mJEi29VPjH.png
   :alt: dashboard cluster tab


Single Job Submission
^^^^^^^^^^^^^^^^^^^^^

This is a simple walkthrough for gke job submission from caliban.

Pre-submission Cluster Status
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In this example, we have an existing cluster with no jobs currently running. You
can inspect the cluster from the GCP dashboard for your project under the
``Kubernetes Engine > Clusters`` menu:


.. image:: https://screenshot.googleplex.com/pWPkUFBUBsH.png
   :target: https://screenshot.googleplex.com/pWPkUFBUBsH.png
   :alt: cluster dashboard


Selecting our ``foo`` cluster, we can see more details:


.. image:: https://screenshot.googleplex.com/V5QfdB6Nbbi.png
   :target: https://screenshot.googleplex.com/V5QfdB6Nbbi.png
   :alt: foo cluster


Here we can see that our cluster has only a single node pool: the default pool
created when we started the cluster. We will submit a job that uses gpu
acceleration, so we will see how the cluster autoscaler will add a new node pool
for our job based on the gpu and machine specs we provide in the job submission.

We can also see here our cluster limits for autoscaling, which are derived from
our zone quota. These limits control how many instances of different accelerator
resources we can get via autoprovisioning. These limits are cluster-wide, so in
this example we can get at most eight K80 gpus, and at most four T4 gpus.

Submit the Job
~~~~~~~~~~~~~~

To submit a job to your cluster, use the ``caliban cluster job submit`` command.
(see `here <http://go/caliban#caliban-cluster-job-submit>`_ and
`here <http://go/caliban-gke#submitting-jobs>`_ for additional examples and
documentation) Here we create our cluster job (some of output elided):

.. code-block:: bash

   aslone@aslone:$ caliban cluster job submit --gpu_spec 1xK80 --name cifar10-test cifar10_resnet_train.sh --
   I0204 11:33:48.564418 139920906995520 core.py:386] Generating Docker image with parameters:
   I0204 11:33:48.565413 139920906995520 core.py:387] {'adc_path': '/usr/local/google/home/aslone/.config/gcloud/application_default_credentials.json',
    'credentials_path': '/usr/local/google/home/aslone/.config/service_keys/aslone_blueshift.json',
    'extra_dirs': None,
    'job_mode': <JobMode.GPU: 2>,
    'package': Package(executable=['/bin/bash'], package_path='.', script_path='cifar10_resnet_train.sh', main_module=None),
    'requirements_path': 'requirements.txt',
    'setup_extras': None}
   I0204 11:33:48.566865 139920906995520 docker.py:497] Running command: docker build --rm -f- /usr/local/google/home/aslone/sw/tensorflow_models
   Sending build context to Docker daemon  1.058GB

   Step 1/15 : FROM gcr.io/blueshift-playground/blueshift:gpu
    ---> 74f198a8ba19

    ...

   6cebf3abed5f: Layer already exists
   latest: digest: sha256:99c759693d78c24d0b6441e70d5b5538541cccaa158142b5896fadebc30b7ab9 size: 6608
   I0204 11:35:12.189604 139920906995520 cli.py:431] submitted job:
   cifar10-test-tsnlf:
   https://pantheon.corp.google.com/kubernetes/job/us-central1-a/foo/default/cifar10-test-tsnlf

Our job has now been submitted to our cluster. Due to various factors, it will
take a short time before the job is actually running. We can use the link
provided by caliban to monitor the life cycle of our job.

Monitor Autoscaling/Job Placement
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When we first submit the job, we will often see that the job shows what appears
to be an error with a big, ugly, red message saying something along the lines of
"unschedulable"


.. image:: https://screenshot.googleplex.com/dye5mDUw8zc.png
   :target: https://screenshot.googleplex.com/dye5mDUw8zc.png
   :alt: scary


We need to look at the 'details' on the right side to see how the Kubernetes pod
associated with this job is progressing. The job right now is unschedulable
because the cluster has not yet scaled up to accomodate our request. Choosing
the 'details' button, we see:


.. image:: https://screenshot.googleplex.com/UuLkkHCVZQN.png
   :target: https://screenshot.googleplex.com/UuLkkHCVZQN.png
   :alt: pod


This is the pod associated with our job. Clicking on this shows us details on
the pod, where we can watch its development. On the pod page, choose the
'Events' tab:


.. image:: https://screenshot.googleplex.com/ccbcYVBJxYU.png
   :target: https://screenshot.googleplex.com/ccbcYVBJxYU.png
   :alt: pod events


Here we can see the progression of the pod. (note that the events here are in
order of 'last seen', so they appear out-of-order when trying to divine the
logical progression of your job) The first event indicates that initially the
cluster does not have any resources to support the pod. The second event shows
that the cluster is scaling up to accomodate this job. This is often the crucial
step. The next relevant event (3) shows that our docker image is being pulled
for our new container. This is then followed by (4) container creation, and then
(5) container start. At this point our job is up and running. Note from the
timestamps that this process took (in this case) approximately ten minutes from
submission to container operation.

While this process is progressing, we can also monitor the cluster and its node
pools from the cluster page:


.. image:: https://screenshot.googleplex.com/dtx1k9LZaMY.png
   :target: https://screenshot.googleplex.com/dtx1k9LZaMY.png
   :alt: cluster node pools


Now we can see that the cluster has auto-provisioned a new node pool for us in
response to our job submission. Exploring this further you can find the new node
instance that was created and inspect its properties. Once your job has
completed, and if there are no more jobs pending, the cluster will scale down,
deleting the compute node and deleting the node pool.

Monitor Job Logs
~~~~~~~~~~~~~~~~

Now that our job is running, we can monitor the logs from the container from the
dashboard using stackdriver (Kubernetes Engine > Workloads > our-job):


.. image:: https://screenshot.googleplex.com/F7prOO7iGKa.png
   :target: https://screenshot.googleplex.com/F7prOO7iGKa.png
   :alt: job details


This will take you to the stackdriver log viewer for the container:


.. image:: https://screenshot.googleplex.com/b9yu5sHPmj3.png
   :target: https://screenshot.googleplex.com/b9yu5sHPmj3.png
   :alt: stackdriver logs


Clean up Job
~~~~~~~~~~~~

Once our job has finished, its logs and other data will persist until we delete
it, even though the container has been stopped and no compute resources are
still active. This is quite useful of course, but at some point you will want to
delete the job (which will delete all of the logs and associated metadata, so
use caution)


.. image:: https://screenshot.googleplex.com/ZQ1mK9LX4Gn.png
   :target: https://screenshot.googleplex.com/ZQ1mK9LX4Gn.png
   :alt: delete job


Cluster Deletion
^^^^^^^^^^^^^^^^

In most cases you will bring up your cluster and leave it running. The cluster
master does consume resources, however, so if you know that you are not going to
be submitting jobs to your cluster for some length of time, you may want to
delete your cluster to save money. Before doing this, please make sure that all
of your jobs are complete, as deleting the cluster will also kill any running
jobs. Deleting the cluster is very straightforward, simply using the
`caliban cluster delete <go/caliban#caliban-cluster-delete>`_ command.
