# Caliban

[![Build status](https://img.shields.io/travis/google/caliban/master.svg?maxAge=3600)](http://travis-ci.org/google/caliban)
[![Codecov branch](https://img.shields.io/codecov/c/github/google/caliban/master.svg?maxAge=3600)](https://codecov.io/github/google/caliban)
[![readthedocs](https://img.shields.io/readthedocs/caliban?maxAge=3600)](https://caliban.readthedocs.io/en/latest/?badge=latest)
[![caliban version](https://img.shields.io/pypi/v/caliban?maxAge=3600)](https://pypi.org/project/caliban)

Caliban is a tool for developing research workflows and notebooks in an
isolated, reproducible computing environment.

Caliban is makes it astonishingly easy to run your code locally, then ship the
exact same code up to a Cloud environment for execution on Big Iron machines.

## Quickstart

[Install Docker](#docker), then install Caliban via pip:

```bash
pip install caliban
```

Train your first [machine learning
model](https://www.tensorflow.org/tutorials/quickstart/beginner) in 2 lines:

```bash
git clone https://github.com/google/caliban.git && cd caliban/tutorials/basic
caliban run --nogpu mnist.py
```

**Next**:

- See the [Installation](#installation-and-prerequisites) section for more detail
- Explore Caliban's more advanced features with ["Getting Started with Caliban"](#getting-started-with-caliban)
- Read the [Overview](#overview) for info on Caliban's subcommands.

Full documentation for Caliban lives at [Read The Docs](https://caliban.readthedocs.io/en/latest).

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

## Installing Caliban and Prerequisites

Caliban's prequisites are [Docker](#docker) and [Python >= 3.7](#python-37).

Make sure your Python is up to date:

```bash
$ python --version
Python 3.7.7 # should be >=3.7.0
```

If not, visit ["Installing Python 3.7"](#python-37) before proceeding.

Next, install Caliban via [pip](https://pypi.org/project/caliban/):

```bash
pip install -U caliban
```

check if your installation worked by navigating to an empty folder and running
`caliban --help`. You should see the usage dialogue:

```bash
$ caliban --help
usage: caliban [-h] [--helpfull] [--version]
               {shell,notebook,build,run,cloud,cluster,status,stop,resubmit}
               ...
```

### Docker

Caliban executes your code inside a "container", managed by
[Docker](https://hub.docker.com/editions/community/docker-ce-desktop-mac). To get Docker:

- On MacOS, follow the installation instructions at [Docker
  Desktop](https://hub.docker.com/editions/community/docker-ce-desktop-mac).
- On Linux, visit the [Docker installation
  instructions](https://docs.docker.com/engine/install/ubuntu/#installation-methods).

### Python 3.7
Make sure your Python version is up to date:

```bash
$ python --version
Python 3.7.7 # should be >=3.7.0
```

If you need to upgrade:

- On MacOS, install the latest Python version from
  [python.org](https://www.python.org/downloads/mac-osx) ([direct
  link](https://www.python.org/ftp/python/3.8.3/python-3.8.3-macosx10.9.pkg)).
- On Linux, run `sudo apt-get update && sudo apt-get install python3.7`.

### Cloud Submission and GPUs

Caliban's [Read the Docs](https://caliban.readthedocs.io/) documentation has
instructions on:

- [Installing the `nvidia-docker`
  runtime](https://caliban.readthedocs.io/en/latest/getting_started/prerequisites.html#docker-and-cuda),
  so you can use Caliban to run jobs that use your Linux machine's GPU.
- [Setting up a Google Cloud
  account](https://caliban.readthedocs.io/en/latest/getting_started/cloud.html)
  so you can submit your code to Google's [Cloud AI
  Platform](https://cloud.google.com/ai-platform) with `caliban cloud`.

## Getting Started with Caliban

This section describes how to use Caliban to train an image-classifying
[Tensorflow neural
network](https://www.tensorflow.org/tutorials/quickstart/beginner) with Caliban.
We'll cover how to:

- Train a neural network on your local machine
- Increase the model's accuracy by changing the [learning
  rate](https://medium.com/octavian-ai/which-optimizer-and-learning-rate-should-i-use-for-deep-learning-5acb418f9b2)
  with a command-line flag
- Sweep across a range of learning rates with Caliban's [experiment
  broadcasting](https://caliban.readthedocs.io/en/latest/explore/experiment_broadcasting.html)
  feature
- Train the model in the Cloud on Google's [AI
  Platform](https://cloud.google.com/ai-platform)
- Develop your code interactively using `caliban shell` in the exact same
  environment.

### Preparing your Project

Create an empty directory and use `curl` to download a [python
script](https://github.com/google/caliban/blob/sritchie/doc_test/tutorials/basic/mnist.py#L16)
that trains a basic neural betwork.

```
mkdir demo && cd demo
curl --output mnist.py https://raw.githubusercontent.com/google/caliban/sritchie/doc_test/tutorials/basic/mnist.py
```

Create a file called `requirements.txt` to declare `tensorflow-cpu` as a dependency:

```bash
echo "tensorflow-cpu" > requirements.txt
```

Caliban will automatically make any entry in `requirements.txt` available when
you run your code. See ["Declaring
Requirements"](https://caliban.readthedocs.io/en/latest/explore/declaring_requirements.html)
for more information.

### Training the Network

Run this command to train your first ML model:

```bash
caliban run --nogpu mnist.py
```

You should see a stream of output ending in this:

```text
Training model with learning rate=0.1 for 3 epochs.
Epoch 1/3
1875/1875 - 3s - loss: 2.0989 - accuracy: 0.2506
Epoch 2/3
1875/1875 - 3s - loss: 1.9222 - accuracy: 0.2273
Epoch 3/3
1875/1875 - 3s - loss: 2.0777 - accuracy: 0.1938
Model performance:
313/313 - 0s - loss: 2.0973 - accuracy: 0.1858
```

Your model was able to recognize digits from the
[MNIST](https://en.wikipedia.org/wiki/MNIST_database) dataset with 18.58%
accuracy. Can we do better?

### Improving the Model

The default learning rate is `0.1`. Run the code again with a smaller learning
rate by passing a command-line flag, separated from your original command by
`--`:

```bash
$ caliban run --nogpu mnist.py -- --learning_rate 0.01

<<elided>>

Training model with learning rate=0.01 for 3 epochs.
Epoch 1/3
1875/1875 - 4s - loss: 0.2676 - accuracy: 0.9221
Epoch 2/3
1875/1875 - 4s - loss: 0.1863 - accuracy: 0.9506
Epoch 3/3
1875/1875 - 4s - loss: 0.1567 - accuracy: 0.9585
Model performance:
313/313 - 0s - loss: 0.1410 - accuracy: 0.9642
```

96% accuracy! Much better! Can we do better still?

### Experiment Broadcasting

Caliban's [experiment
broadcasting](https://caliban.readthedocs.io/en/latest/explore/experiment_broadcasting.html)
feature will allow us to run many jobs with different sets of arguments.

Create a file called `experiment.json` with a
[JSON](https://www.json.org/json-en.html) dictionary of the format
`{"flag_name": ["list", "of", "values"]}`:

```bash
echo '{"learning_rate": [0.01, 0.001, 0.0001]}' > experiment.json
```

Pass the config with `--experiment_config` and run again:

```bash
caliban run --experiment_config experiment.json --nogpu mnist.py
```

You should see accuracies of roughly `0.9493`, `0.9723` and `0.9537`. Looks like
`0.001` is a nice choice (unless I'm
[overfitting??](https://www.reddit.com/r/MachineLearning/comments/81o4f0/d_does_most_research_in_ml_overfit_to_the_test/))

### Submitting to Cloud AI Platform

Now it's time to submit the job to [Cloud AI
Platform](https://cloud.google.com/ai-platform).

(**NOTE**: This section requires a Google Cloud account. You can create a free
account with $300 of credit to get started. Follow Caliban's ["Getting Started
with Google
Cloud"](https://caliban.readthedocs.io/en/latest/getting_started/cloud.html)
documentation, then come back here to proceed.**

Submit the job to AI Platform by changing the word `run` to `cloud`:

```bash
caliban cloud --nogpu mnist.py -- --learning_rate 0.01
```

You should see output like this:

```bash
I0615 19:57:43.354172 4563361216 core.py:161] Job 1 - jobId: caliban_totoro_1, image: gcr.io/research-3141/974a776e6037:latest
I0615 19:57:43.354712 4563361216 core.py:161] Job 1 - Accelerator: {'count': 0, 'type': 'ACCELERATOR_TYPE_UNSPECIFIED'}, machine: 'n1-highcpu-32', region: 'us-central1'
I0615 19:57:43.355082 4563361216 core.py:161] Job 1 - Experiment arguments: ['--learning_rate', '0.01']
I0615 19:57:43.355440 4563361216 core.py:161] Job 1 - labels: {'gpu_enabled': 'false', 'tpu_enabled': 'false', 'job_name': 'caliban_totoro', 'learning_rate': '0_01'}

I0615 19:57:43.356621 4563361216 core.py:324] Submitting request!
I0615 19:57:45.078382 4563361216 core.py:97] Request for job 'caliban_totoro_20200615_195743_1' succeeded!
I0615 19:57:45.078989 4563361216 core.py:98] Job URL: https://console.cloud.google.com/ai-platform/jobs/caliban_totoro_20200615_195743_1?projectId=totoro-project
I0615 19:57:45.079524 4563361216 core.py:100] Streaming log CLI command: $ gcloud ai-platform jobs stream-logs caliban_totoro_20200615_195743_1
Submitting caliban_totoro_1: 100%|####################################################################################################################################################################################| 1/1 [00:02<00:00,  2.65s/requests]
I0615 19:57:45.405600 4563361216 core.py:673]
I0615 19:57:45.405819 4563361216 core.py:676] Visit https://console.cloud.google.com/ai-platform/jobs/?projectId=research-3141 to see the status of all jobs.
I0615 19:57:45.405959 4563361216 core.py:677]
```

This means that Caliban has:

- built a Docker container with all of your code
- Pushed that container up to Google Cloud's [Container
  Registry](https://cloud.google.com/container-registry)
- Submitted the job to [AI Platform](https://cloud.google.com/ai-platform).

You can now visit the link in the output that looks like:
https://console.cloud.google.com/ai-platform/jobs/caliban_totoro_20200615_195743_1?projectId=totoro-project
to see all of your job's logs.

#### Why do I need Cloud?

With Google Cloud, you can use on-demand
[GPUs](https://caliban.readthedocs.io/en/latest/cloud/gpu_specs.html) and
[TPUs](https://caliban.readthedocs.io/en/latest/cloud/ai_platform_tpu.html) and
train models on large datasets at very high speeds. You can also customize the
[machine
type](https://caliban.readthedocs.io/en/latest/cloud/gpu_specs.html#custom-machine-types)
that AI Platform uses to run your job. You might need high memory or more CPU,
for example.

See Caliban's ["Customizing Machines and
GPUs"](https://caliban.readthedocs.io/en/latest/cloud/gpu_specs.html#) for more
information.

### Interactive Development with `caliban shell`

[`caliban
shell`](https://caliban.readthedocs.io/en/latest/cli/caliban_shell.html) lets
you develop code interactively inside of the exact same environment that your
code will have available, locally during `caliban run` or in the Cloud with
`caliban cloud`.

Run the following command to activate the shell:

```bash
caliban shell --nogpu
```

You should see Caliban's terminal:

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

You're now living in an isolated [Docker
container](https://www.docker.com/resources/what-container) with your
`tensorflow-cpu` dependency available (and any others [you've
declared](https://caliban.readthedocs.io/en/latest/explore/declaring_requirements.html)).

Run the `python` command and check that `tensorflow` is installed:

```bash
$ python
Python 3.6.9 (default, Nov  7 2019, 10:44:02)
[GCC 8.3.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import tensorflow as tf
>>> tf.__version__
'2.2.0'
```

Your home directory and the folder where you ran the command are both mounted
into this isolated environment, so any changes you make to either of those
directories will be reflected immediately.

Any code you add to the current folder and edit on your computer will be
available in this special Caliban shell. Run the example from before like this:

```
python mnist.py --learning_rate 0.01
```

If your code runs in `caliban shell`, you can be almost certain that your code
will execute in a Cloud environment, with potentially many GPUs attached and
much larger machines available.

### What next?

Read the [Overview](#overview) for more information on Caliban's subcommands,
then head over to [Caliban's documentation
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

If Caliban helps you in your research, please consider citing the repository:

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
