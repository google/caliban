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
