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

![](https://upload.wikimedia.org/wikipedia/commons/a/ad/Stephano%2C_Trinculo_and_Caliban_dancing_from_The_Tempest_by_Johann_Heinrich_Ramberg.jpg)

> “Be not afeard; the isle is full of noises,
> Sounds, and sweet airs, that give delight and hurt not.
> Sometimes a thousand twangling instruments
> Will hum about mine ears; and sometime voices,
> That, if I then had waked after long sleep,
> Will make me sleep again: and then, in dreaming,
> The clouds methought would open, and show riches
> Ready to drop upon me; that, when I waked,
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

## Overview

Caliban provides five subcommands that you run inside some directory on your
laptop or workstation:

* [caliban shell]() generates a Docker image containing any dependencies you've
  declared in a `requirements.txt` and/or `setup.py` in the directory and opens
  an interactive shell in that directory. The `caliban shell` environment is
  ~identical to the environment that will be available to your code when you
  submit it to AI Platform; the difference is that your current directory is
  live-mounted into the container, so you can develop interactively.

* [caliban notebook]() starts a Jupyter notebook or lab instance inside of a
  docker image containing your dependencies; the guarantee about an environment
  identical to AI Platform applies here as well.

* [caliban run]() packages your directory's code into the Docker image and
  executes it locally using `docker run`. If you have a workstation GPU, the
  instance will attach to it by default - no need to install the CUDA toolkit.
  The docker environment takes care of all that. This environment is truly
  identical to the AI Platform environment. The docker image that runs locally
  is the same image that will run in AI Platform.

* [caliban cloud]() allows you to submit jobs to AI Platform that will run
  inside the same docker image you used with `caliban run`. You can submit
  hundreds of jobs at once. Any machine type, GPU count, and GPU type
  combination you specify will be validated client side, so you'll see an
  immediate error with suggestions, rather than having to debug by submitting
  jobs over and over.

* [caliban build]() builds the docker image used in `caliban cloud` and `caliban
  run` without actually running the container or submitting any code.

* [caliban cluster]() creates GKE clusters and submits jobs to GKE clusters.

## Getting Started

To start using Caliban, navigate into some folder on your computer and run:

```bash
caliban shell --nogpu
```

This command will drop you into a terminal:

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

## Disclaimer

This is a research project, not an official Google product. Expect bugs and
sharp edges. Please help by trying out Caliban, [reporting
bugs](https://github.com/google/caliban/issues), and letting us know what you
think!

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
