# Caliban

[![Build status](https://img.shields.io/travis/google/caliban/master.svg?maxAge=3600)](http://travis-ci.org/google/caliban)
[![Codecov branch](https://img.shields.io/codecov/c/github/google/caliban/master.svg?maxAge=3600)](https://codecov.io/github/google/Latest)
[![readthedocs](https://img.shields.io/readthedocs/caliban?maxAge=3600)](https://caliban.readthedocs.io/en/latest/?badge=latest)
[![caliban version](https://img.shields.io/pypi/v/caliban?maxAge=3600)](https://pypi.org/project/caliban)

Caliban is a tool for developing research workflow and notebooks in an isolated
Docker environment and submitting those isolated environments to Google Compute
Cloud.

Caliban makes it astonishingly easy to develop and execute code locally, and
then ship the exact same code up to a Cloud environment for execution on Big
Iron machines.

**To get started**:

- see the [Installation](#installation-and-prerequisites) section below, then
- visit the short tutorial at the ["Getting Started"](#getting-started) section.
- Next steps for exploration are outlined at ["What Next?"](#what-next), and
- the [Overview](#overview) provides some more flavor on the various subcommands
  that Caliban provides.

Full documentation for Caliban lives at [Read The
Docs](https://caliban.readthedocs.io/en/latest).

<p align="center">
<img src="https://upload.wikimedia.org/wikipedia/commons/a/ad/Stephano%2C_Trinculo_and_Caliban_dancing_from_The_Tempest_by_Johann_Heinrich_Ramberg.jpg" align="center" width="500">
</p>

> “Be not afeard; the isle is full of noises, \
> Sounds, and sweet airs, that give delight and hurt not. \
> Sometimes a thousand twangling instruments \
> Will hum about mine ears; and sometime voices, \
> That, if I then had waked after long sleep, \
> Will make me sleep again: and then, in dreaming, \
> The clouds methought would open, and show riches \
> Ready to drop upon me; that, when I waked, \
> I cried to dream again.”
>
> -- <cite>Shakespeare, The Tempest</cite>

## Installation and Prerequisites

Caliban lives on [PyPI](https://pypi.org/project/caliban/), so installation is
as easy as:

```bash
pip install -U caliban
```

If you want to make Caliban available globally, we recommend installing via
[pipx](https://pipxproject.github.io/pipx/installation/). [Get pipx installed](https://pipxproject.github.io/pipx/installation/), and then run:

```bash
pipx install caliban
```

To run any commands, you'll need to install [Docker](https://www.docker.com/), and make sure your Python version is >= 3.7.0:

```bash
$ python --version
Python 3.7.7
```

On a Mac, install [python](https://www.python.org/downloads/mac-osx) and
[Docker](https://hub.docker.com/editions/community/docker-ce-desktop-mac), and
check if your installation is working by navigating to some empty folder and
running:

```bash
$ caliban --help
usage: caliban [-h] [--helpfull] [--version]
               {shell,notebook,build,run,cloud,cluster,status,stop,resubmit}
               ...
```

Our more detailed [Getting
Started](https://caliban.readthedocs.io/en/latest/getting_started/prerequisites.html)
documentation has instructions for Linux boxes, `nvidia-docker` setup and Google
Cloud credential configuration. Armed with these tools you'll be able to run
scripts locally using a your GPU or submit caliban-dockerized jobs to Cloud.

Now that you have Caliban installed:

- see the [Getting Started](#getting-started) section below, or
- read the [Overview](#overview) for a discussion of Caliban's subcommands.

## Overview

Caliban provides five subcommands that you run inside some project directory on
your machine:

* [`caliban
  shell`](https://caliban.readthedocs.io/en/latest/cli/caliban_shell.html)
  generates a Docker image containing any dependencies you've declared in a
  `requirements.txt` and/or `setup.py` in the directory and opens an interactive
  shell in that directory. The `caliban shell` environment is ~identical to the
  environment that will be available to your code when you submit it to AI
  Platform; the difference is that your current directory is live-mounted into
  the container, so you can develop interactively.

* [`caliban
  notebook`](https://caliban.readthedocs.io/en/latest/cli/caliban_notebook.html)
  starts a Jupyter notebook or lab instance inside of a docker image containing
  your dependencies; the guarantee about an environment identical to AI Platform
  applies here as well.

* [`caliban run`](https://caliban.readthedocs.io/en/latest/cli/caliban_run.html)
  packages your directory's code into the Docker image and executes it locally
  using `docker run`. If you have a GPU, the instance will attach to it by
  default - no need to install the CUDA toolkit. The docker environment takes
  care of all that. This environment is truly identical to the AI Platform
  environment. The docker image that runs locally is the same image that will
  run in AI Platform.

* [`caliban
  cloud`](https://caliban.readthedocs.io/en/latest/cli/caliban_cloud.html) allows
  you to submit jobs to AI Platform that will run inside the same docker image
  you used with `caliban run`. You can submit hundreds of jobs at once. Any
  machine type, GPU count, and GPU type combination you specify will be
  validated client side, so you'll see an immediate error with suggestions,
  rather than having to debug by submitting jobs over and over.

* [`caliban
  build`](https://caliban.readthedocs.io/en/latest/cli/caliban_build.html) builds
  the docker image used in `caliban cloud` and `caliban run` without actually
  running the container or submitting any code.

* [`caliban
  cluster`](https://caliban.readthedocs.io/en/latest/cli/caliban_cluster.html)
  creates GKE clusters and submits jobs to GKE clusters.

## Getting Started

This first example will show you how to use Caliban to run a short script inside
of a Caliban-generated Docker container, then submit that script to AI Platform.

Make a new project folder and create a small script:

```bash
mkdir project && cd project
echo "import platform; print(f\"Hello, World, from a {platform.system()} machine.\")" > hello.py
```

Run the script with your local Python executable:

```bash
$ python hello.py
Hello, World, from a Darwin machine.
```

Use Caliban to run the same script inside a Docker container:

```bash
caliban run --nogpu hello.py
...elided...

0611 15:12:44.371632 4389141952 docker.py:781] Running command: docker run --ipc host 58a1a3bf6145
Hello, World, from a Linux machine.
I0611 15:12:45.000511 4389141952 docker.py:738] Job 1 succeeded!
```

Change a single word to submit the same script to [Google's AI
Platform](https://cloud.google.com/ai-platform):

```bash
caliban cloud --nogpu hello.py
```

(For this last step to work, you'll need to set up a Google Cloud account by
following [these
instructions](https://caliban.readthedocs.io/en/latest/getting_started/cloud.html)).

### Slightly Expanded

This next example shows you how to do interactive development using [`caliban
shell`](https://caliban.readthedocs.io/en/latest/cli/caliban_shell.html). Once
you get your script working, you can use [`caliban
run`](https://caliban.readthedocs.io/en/latest/cli/caliban_run.html) and
[`caliban
cloud`](https://caliban.readthedocs.io/en/latest/cli/caliban_cloud.html) on the
script, just like above.

Run the following command in the `project` folder you created earlier:

```bash
caliban shell --nogpu
```

If this is your first command, you'll see quite a bit of activity as Caliban
downloads its base image to your machine and builds your first container. After
this passes, you should see Caliban's terminal:

```
I0611 12:33:17.551121 4500135360 docker.py:911] Running command: docker run --ipc host -w /usr/app -u 735994:89939 -v /Users/totoro/code/example:/usr/app -it --entrypoint /bin/bash -v /Users/totoro:/home/totoro ab8a7d7db868
   _________    __    ________  ___    _   __  __  __
  / ____/   |  / /   /  _/ __ )/   |  / | / /  \ \ \ \
 / /   / /| | / /    / // __  / /| | /  |/ /    \ \ \ \
/ /___/ ___ |/ /____/ // /_/ / ___ |/ /|  /     / / / /
\____/_/  |_/_____/___/_____/_/  |_/_/ |_/     /_/ /_/

You are running caliban shell as user with ID 735994 and group 89939,
which should map to the ID and group for your user on the Docker host. Great!

[totoro@6a9b28990757 /usr/app]$
```

You're now living in an isolated Docker container, running Linux, with a clean
virtual environment available. Your home directory and the folder where you ran
the command are both live-mounted into the container, so any changes you make to
either of those directories will be reflected immediately.

Type `C-d` to exit the container.

Create a new file called `requirements.txt` in the folder and add the
`tensorflow` dependency, then run `caliban shell` again:

```bash
echo tensorflow >> requirements.txt
caliban shell --nogpu
```

You should see more activity as `caliban` builds a new container with
`tensorflow` installed. This time, inside your container, run `python` and check
that `tensorflow` is installed:

```bash
$ python
Python 3.6.9 (default, Nov  7 2019, 10:44:02)
[GCC 8.3.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import tensorflow as tf
>>> tf.__version__
'2.2.0'
python
```

Any code you write in this folder will be accessible in the shell. If it works
at `caliban shell`, you can be almost certain that your code will execute in a
Cloud environment, with potentially many GPUs attached and much larger machines
available.

*and* you didn't have to write a single Dockerfile!

### What next?

Next, you might want to explore:

- [triggering hundreds of jobs from an experiment
  config](https://caliban.readthedocs.io/en/latest/explore/experiment_groups.html)
- Submitting jobs to Google Cloud with [`caliban
  cloud`](https://caliban.readthedocs.io/en/latest/cli/caliban_cloud.html)
- Working in a Jupyter notebook in the same, isolated environment where your
  production code will run via [`caliban
  notebook`](https://caliban.readthedocs.io/en/latest/cli/caliban_notebook.html)

There is a lot to explore. Head over to [Caliban's documentation
site](https://caliban.readthedocs.io/en/latest/) and check out the links on the
sidebar.

If you find anything confusing, please feel free to [create an
issue](https://github.com/google/caliban/issues) on our [Github Issues
page](https://github.com/google/caliban/issues), and we'll get you sorted out.

## Disclaimer

This is a research project, not an official Google product. Expect bugs and
sharp edges. Please help by trying out Caliban, [reporting
bugs](https://github.com/google/caliban/issues), and letting us know what you
think!

## Contributing

Please refer to our [Contributor's Guide](CONTRIBUTING.md) for information on
how to get started contributing to Caliban.

## Citing Caliban

If Caliban helps you in your research, pleae consider citing the repository:

```
@software{caliban2020github,
  author = {Vinay Ramasesh and Sam Ritchie and Ambrose Slone},
  title = {{Caliban}: Docker-based job manager for reproducible workflows},
  url = {http://github.com/google/caliban},
  version = {0.1.0},
  year = {2020},
}
```

In the above bibtex entry, names are in alphabetical order, the version number
is intended to be that of the latest tag on github, and the year corresponds to
the project's open-source release.

## License

Copyright 2020 Google LLC.

Licensed under the [Apache License, Version 2.0](http://www.apache.org/licenses/LICENSE-2.0).
