# Caliban

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

## Overview

Caliban is a tool for developing research workflow and notebooks in an isolated
Docker environment and submitting those isolated environments to Google Compute
Cloud.

## Prerequisites

Before you can install and use Caliban to manage your research workflows, you'll
need a solid Cloud and Docker installation. Follow these steps to get set up.

### Python 3

Make sure your `python3` is up to date by running the following command at your workstation:

```bash
sudo apt-get install python3 python3-venv python3-pip
```

If you're on a Mac, download [Python 3.7.5 from
python.org](https://www.python.org/downloads/mac-osx) ([direct download
link](https://www.python.org/ftp/python/3.7.5/python-3.7.5-macosx10.9.pkg))

Once that's all set, verify that you're running python 3.6 or above:

```bash
$ python3 --version
Python 3.7.5 # Or something above 3.6.0
```

### Blueshift Internal Repo

The [Blueshift internal
repository](https://team.git.corp.google.com/blueshift/blueshift/) has some nice
tooling that will make life easier at Blueshift.

To get the Blueshift repository installed, run these three commands:

```bash
git clone sso://team/blueshift/blueshift ~/dev/blueshift
echo -e '\n#Blueshift shared aliases and functions\nsource ~/dev/blueshift/profile/bashrc' >> ~/.bashrc
source ~/.bashrc
```

Please modify the above if you're using a different shell like `zsh`.

### Docker and CUDA

Caliban uses Docker for all of its tasks. To use Caliban, you'll need `docker``
and `nvidia-docker` on your machine. Use Blueshift's [Working with
Docker](https://g3doc.corp.google.com/company/teams/blueshift/guide/docker.md?cl=head)
tutorial to get yourself set up. This page lives at <https://go/blueshift-dev>
if you'd like to find it again.

If you're on a Mac laptop, just install [Docker Desktop for
Mac](https://docs.docker.com/docker-for-mac/install/) (so easy!)

If you're on a workstation, you'll also need to make sure that your CUDA drivers
are up to date, and that you have a big-iron GPU installed in your workstation.

If you've installed the [Blueshift
repository](https://team.git.corp.google.com/blueshift/blueshift/) this part's
easy. Just open a new terminal window. If you don't see any warnings about CUDA,
you're set!

If you still need to install a physical GPU in your workstation, the
[Workstation GPU
installation](https://g3doc.corp.google.com/company/teams/blueshift/guide/gpu_install.md?cl=head)
tutorial will get you sorted.

## Getting Caliban

If you've already installed the [Blueshift internal
repository](https://team.git.corp.google.com/blueshift/blueshift/), the easiest
way to get Caliban is to run the following in your terminal:

```bash
install_caliban
```

This command will install the `caliban` command into its own isolated virtual
environment and make the command globally available.

### Manual Installation

If you don't have the Blueshift repo installed, or if the above is failing, here
are the steps, written out more exhaustively.

If you're currently in a `virtualenv`, please run `deactivate` to disable it
before proceeding.

We'll install `caliban` using `pipx`. `pipx` is a tool that lets you install
command line utilities written in Python into their own virtual environments,
completely isolated from your system python packages or other virtualenvs.

Install `pipx` like this:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

Once `pipx` is installed, use it to install `caliban`:

```bash
pipx install -e --spec git+sso://team/blueshift/caliban caliban
```

You may need to run `gcert` to get this to work.

### Check your Installation

To check if all is well, run

```bash
caliban --help
```

to see the list of subcommands. We'll explore the meaning of each command below.

## Using Caliban

If you want to practice using Caliban with a proper getting-started style guide,
head over to Blueshift's [Hello
World](https://team.git.corp.google.com/blueshift/hello-world/) repository.

Read on for information on the specific commands exposed by Caliban.

### caliban shell

This command is designed for fast, iterative workflows on scripts in an
environment that's guaranteed to match the environment available to your code on
Cloud.

Running `caliban shell` in any directory will generate a Docker image containing
the minimal environment necessary to execute Python ML workflows and drop you
into an interactive shell inside of that image.

Caliban will copy in your Cloud credentials and set the required
`$GOOGLE_APPLICATION_CREDENTIALS` env variable, so all Cloud interaction from
Python should Just Work.

The base Caliban images also have `gcloud` installed; all `gcloud` and `gsutil`
commands will work with the same permissions granted to the key found at
`$GOOGLE_APPLICATION_CREDENTIALS`.

NOTE: If you run `caliban shell --bare`, your gcloud and gsutil will have the
same permissions that they'll have in the cloud - the permissions granted by
your JSON key file. If you just run `caliban shell`, which mounts your home
directory, `gcloud` and `gsutil` will preferentially load the config you have on
your local machine.

The only python dependencies available in the container will be dependencies
that you declare explicitly in either:

- a `requirements.txt` file
- a `setup.py` file.

Your setup file can declare groups of dependencies using the setuptools
[extras_require](https://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies)
feature. See the [setup.py file from our Hello
World](https://team.git.corp.google.com/blueshift/hello-world/+/320b991640c9597664c93cd2d584ca37f5e05ce3/setup.py)
project for an example of how to use `extras_require` to create separate
environments for GPU and CPU.

By default your home directory will mount into the container, along with the
folder you're in when you run `caliban shell`. This means that:

- your default bash (or zsh) environment will be available to you at the
  `caliban shell`.
- Any changes you make to files in the mounted directory will be immediately
  available to you to run with, say, `python -m trainer.train` or some similar
  command.

On the Mac you'll have to pass `--nogpu` to `shell`, as the NVIDIA runtime isn't
supported on non-Linux machines.

`caliban shell` supports the following arguments:

```bash
usage: caliban shell [-h] [--helpfull] [--nogpu] [-e EXTRAS] [--bare]

optional arguments:
  -h, --help            show this help message and exit
  --helpfull            show full help message and exit
  --nogpu               Disable GPU mode and force CPU-only.
  -e EXTRAS, --extras EXTRAS
                        setup.py dependency keys.
  --bare                Skip mounting the $HOME directory; load a bare shell.
```

### caliban notebook

This command generates the same isolated environment as the other commands, but
instead of running your code or dropping you into a shell, runs a local instance
of Jupyter based in the folder where you execute the command.

By default `caliban notebook` runs `jupyter notebook` inside the container. To
run Jupyterlab, pass the `--lab` flag:

```bash
caliban notebook --lab
```

As with the other commands, the only python dependencies available in the
container will be dependencies that you declare explicitly in either:

- a `requirements.txt` file
- a `setup.py` file.

Your setup file can declare groups of dependencies using the setuptools
[extras_require](https://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies)
feature. See the [setup.py file from our Hello
World](https://team.git.corp.google.com/blueshift/hello-world/+/320b991640c9597664c93cd2d584ca37f5e05ce3/setup.py)
project for an example of how to use `extras_require` to create separate
environments for GPU and CPU.

`caliban notebook` mounts your `$HOME` directory into the container, which
allows your Jupyter settings to persist across sessions. If you don't want this
for some reason, run the command with the `--bare` flag.

If you'd like to run `notebook` using a different port, use the `--port` option:

```bash
caliban notebook --lab --port 8889
```

On the Mac you'll have to pass `--nogpu` to `notebook`, as the NVIDIA runtime
isn't supported on non-Linux machines.

`caliban notebook` supports the following arguments:

```bash
usage: caliban shell [-h] [--helpfull] [--nogpu] [-e EXTRAS] [--bare]

optional arguments:
  -h, --help            show this help message and exit
  --helpfull            show full help message and exit
  --nogpu               Disable GPU mode and force CPU-only.
  -e EXTRAS, --extras EXTRAS
                        setup.py dependency keys.
  --bare                Skip mounting the $HOME directory; load a bare shell.
(deep) [samritchie@samritchie-macbookpro ~/code/python/caliban (sritchie/cli_updates)]$ caliban notebook --help
usage: caliban notebook [-h] [--helpfull] [--nogpu] [-e EXTRAS] [-p PORT]
                        [-jv JUPYTER_VERSION] [--lab] [--bare]

optional arguments:
  -h, --help            show this help message and exit
  --helpfull            show full help message and exit
  --nogpu               Disable GPU mode and force CPU-only.
  -e EXTRAS, --extras EXTRAS
                        setup.py dependency keys.
  -p PORT, --port PORT  Port to use for Jupyter, inside container and locally.
  -jv JUPYTER_VERSION, --jupyter_version JUPYTER_VERSION
                        Jupyterlab version to install via pip.
  --lab                 run 'jupyter lab', vs the default 'jupyter notebook'.
  --bare                Skip mounting the $HOME directory; run an isolated
                        Jupyter lab.
```

### caliban run

This command bundles your code and any other directories you specify into an
isolated Docker container and runs the resulting Python code on your local
machine, but inside of the Docker environment.

Because the container is completely isolated, to get any results from `caliban
run` you'll have to depend on either:

- `stdout`, if you're just interested in checking if the job is running at all
  before submission to Cloud, for example, or
- Cloud buckets for persistence.

Your credentials are set up inside the container and available via the required
`$GOOGLE_APPLICATION_CREDENTIALS` environment variable, so all Cloud access via
Python should Just Work.

The base Caliban images also have `gcloud` installed; all `gcloud` and `gsutil`
commands will work with the same permissions granted to the key found at
`$GOOGLE_APPLICATION_CREDENTIALS`.

As with the other commands, the only python dependencies available in the
container will be dependencies that you declare explicitly in either:

- a `requirements.txt` file
- a `setup.py` file.

Your setup file can declare groups of dependencies using the setuptools
[extras_require](https://setuptools.readthedocs.io/en/latest/setuptools.html#declaring-extras-optional-features-with-their-own-dependencies)
feature. See the [setup.py file from our Hello
World](https://team.git.corp.google.com/blueshift/hello-world/+/320b991640c9597664c93cd2d584ca37f5e05ce3/setup.py)
project for an example of how to use `extras_require` to create separate
environments for GPU and CPU.

The most basic way to trigger a run is by passing a file path or a module name.
Any of the following will work:

```bash
caliban run trainer.train -- --epochs 2
caliban run trainer/train.py
caliban run mycode.py
caliban run mycode -- learning_rates '[1,2,3]'
```

Any flags or commands you pass to the command after `--` will be passed along,
untouched, to your Python code. By configuring your job with flags you can get a
large range of behavior out of the same module.

If you specify a Python module inside of a folder, `caliban run` will copy only
that folder into the Docker environment. If your script lives in the root, as in
the `mycode.py` example above, the entire current working directory will be
copied in.

This could be inefficient if your directory has lots of data you don't want, or
a folder of notebooks; if you want a smaller build image you can move your
script into a folder. Make sure to create `__init__.py` inside the folder to
make it a proper module.

In addition to the required module name, `caliban run` supports many optional
arguments. All of these must be supplied **before** the module name.

To toggle GPU mode on or off, use `--gpu` or `--nogpu`.

If you want to make extra directories available inside your container, pass them
like this:

```bash
caliban -d data -d models/stored trainer.train
```

This invocation will copy the `data` and `models/stored` directories into the
container, where they can be accessed using a relative path. All directories
must exist relative to the directory where you run `caliban run`.

`caliban run` supports the following arguments:

```bash
usage: caliban run [-h] [--helpfull] [--nogpu] [-e EXTRAS] [-d DIR] module ...

positional arguments:
  module                Code to execute, in either 'trainer.train' or
                        'trainer/train.py' format.

optional arguments:
  -h, --help            show this help message and exit
  --helpfull            show full help message and exit
  --nogpu               Disable GPU mode and force CPU-only.
  -e EXTRAS, --extras EXTRAS
                        setup.py dependency keys.
  -d DIR, --dir DIR     Extra directories to include. List these from large to
                        small to take full advantage of Docker's build cache.

pass-through arguments:
  script_args           This is a catch-all for arguments you want to pass
                        through to your script. any unfamiliar arguments will
                        just pass right through.
```

### caliban cloud

This command bundles your code and any other directories you specify into an
isolated Docker container and runs the resulting Python code on [Google's AI
Platform](https://cloud.google.com/ai-platform/).

To use this mode you'll need to configure your machine for Cloud access using
the tutorial at Blueshift's [Setting up
Cloud](https://g3doc.corp.google.com/company/teams/blueshift/guide/cloud.md?cl=head)
page.

Specifically, you'll need to make sure the following environment variables are set:

- `$PROJECT_ID`: The ID of the Cloud project where you'll be submitting jobs.
- `$GOOGLE_APPLICATION_CREDENTIALS`: a local path to your JSON google creds file.

`caliban cloud` works almost exactly like `caliban run` (by design!). Thanks to
Docker, the environment available to your job on Cloud will look exactly like
the environment available on local.

This means that if you can get your job running in `caliban local` mode you can
be quite sure that it'll complete in Cloud as well. The advantages of Cloud mode
are:

1. The machines are much bigger
2. Multi-GPU machines, clusters and TPUs are available (though clusters and TPUs
   aren't yet supported by caliban)
3. Cloud can execute up to 40 jobs in parallel, and will pipeline many more for
   you.

See the `caliban run` docs for a detailed walkthrough of most options available
to `caliban cloud`.

All user arguments will be passed to cloud as labels, which means that you can
filter by these labels in the AI platform jobs UI (run `ai_job` in a shell if
you've got the [Blueshift
repo](https://team.git.corp.google.com/blueshift/blueshift/) installed).

The additional options available to cloud are:

- **project_id**: This is the ID of the Cloud project that Caliban will use to
  push Docker containers and to submit AI platform jobs. By default Caliban will
  examine your environment for a `$PROJECT_ID` variable; if neither is set and
  you attempt to run a Cloud command, Caliban will exit.
- **region**: The Cloud region you specify with this flag is used for AI
  Platform job submission. Any value listed in the "Americas" section of [AI
  Platform's region docs](https://cloud.google.com/ml-engine/docs/regions) is
  valid (Let us know if you need global regions!). If you don't specify a region
  Caliban will examine your environment for a `$REGION` variable and use this if
  supplied; if that's not set it will default to `"us-central1"`. See `caliban
  cloud --help` for all possible arguments.
- **--machine_type**: Specifies the type of machine to use for each submitted AI
  platform job. See `caliban cloud --help` for all possible values.
- **--gpu_spec**: optional argument of the form GPU_COUNTxGPU_TYPE. See `caliban
  cloud --help` for all possible GPU types, and for the default. Usually 1, 2, 4
  or 8 of each are supported, though this depends on the machine type you
  specify. Caliban will throw a validation error and give you a suggestion for
  how to proceed if you supply a combination that's not possible on AI Platform.
- **--force**: If supplied, this flag will disable all validations on
  combinations of region, machine type, GPU count and GPU type and force caliban
  to submit the job to AI Platform as specified. This is useful in case some new
  GPU was added to a region or machine type and caliban hasn't yet been updated.
- **--name**: If you pass a string via this optional flag, `caliban cloud` will
  submit your job with a job id of "{name}_{timestamp}" and add a
  `job_name:{name}` label to your job. It's useful to pass the same name for
  MANY jobs and use this field to group various experiment runs. (If you think
  this flag should be named something else, tell samritchie@google.com)
- **--experiment_config**: If you pass the location (relative or absolute) of a
  local JSON file of the proper format, caliban will generate many jobs using
  this experiment config and submit them all in batch to AI platform. The
  formatting rules are - keys must be strings, values can be list, int, boolean
  or string. If the value is a list, caliban will generate N copies of the
  experiment config, 1 for each entry in the list, and submit a job for each.
  The total number of jobs submitted is the cardinality of the cartesian product
  of all lists in the experiment config.
- **--label**: You can use this flag to pass many labels to `caliban cloud`;
  just pass the flag over and over. Labels must be of the form `k=v`; `--label
  epochs=2`, for example. If you pass any labels identical to your flags these
  labels will take precedence.
- **--dry_run**: this flag will force logging output of all jobs that caliban
  will submit without the `--dry_run` flag. Docker will also skip an actual
  build and push. Use this to check that your other arguments are well formatted
  before submitting a potentially very large batch of jobs (depending on your
  experiment config).

`caliban cloud` supports the following arguments:

```bash
usage: caliban cloud [-h] [--helpfull] [--nogpu] [-e EXTRAS] [-d DIR]
                     [--project_id PROJECT_ID] [--region REGION]
                     [--machine_type MACHINE_TYPE] [--gpu_spec NUMxGPU_TYPE]
                     [--force] [--name NAME]
                     [--experiment_config EXPERIMENT_CONFIG] [-l KEY=VALUE]
                     [--dry_run]
                     module ...

positional arguments:
  module                Code to execute, in either 'trainer.train' or
                        'trainer/train.py' format.

optional arguments:
  -h, --help            show this help message and exit
  --helpfull            show full help message and exit
  --nogpu               Disable GPU mode and force CPU-only.
  -e EXTRAS, --extras EXTRAS
                        setup.py dependency keys.
  -d DIR, --dir DIR     Extra directories to include. List these from large to
                        small to take full advantage of Docker's build cache.
  --project_id PROJECT_ID
                        ID of the GCloud AI Platform project to use for Cloud
                        job submission and image persistence. (Defaults to
                        $PROJECT_ID; errors if both the argument and
                        $PROJECT_ID are empty.)
  --region REGION       Region to use for Cloud job submission and image
                        persistence. Must be one of ['us-west1', 'us-east1',
                        'us-east4', 'us-west2', 'us-central1', 'europe-west1',
                        'europe-west4', 'europe-north1', 'asia-southeast1',
                        'asia-east1', 'asia-northeast1']. (Defaults to $REGION
                        or 'us-central1'.)
  --machine_type MACHINE_TYPE
                        Cloud machine type to request. Must be one of
                        ['n1-highcpu-64', 'n1-highmem-4', 'n1-standard-16',
                        'n1-standard-96', 'n1-highmem-16', 'n1-highmem-96',
                        'n1-highmem-64', 'n1-highcpu-96', 'n1-standard-64',
                        'n1-highmem-32', 'n1-standard-8', 'n1-highcpu-32',
                        'n1-standard-32', 'n1-highmem-2', 'n1-highcpu-16',
                        'n1-highmem-8', 'n1-standard-4', 'cloud_tpu'].
                        Defaults to 'n1-standard-8' in GPU mode, or
                        'n1-highcpu-32' if --nogpu is passed.
  --gpu_spec NUMxGPU_TYPE
                        Type and number of GPUs to use for each AI Platform
                        submission. Defaults to 1xP100 in GPU mode or None if
                        --nogpu is passed.
  --force               Force past validations and submit the job as
                        specified.
  --name NAME           Set a job name for AI Platform jobs.
  --experiment_config EXPERIMENT_CONFIG
                        Path to an experiment config.
  -l KEY=VALUE, --label KEY=VALUE
                        Extra label k=v pair to submit to Cloud.
  --dry_run             Don't actually submit; log everything that's going to
                        happen.

pass-through arguments:
  script_args           This is a catch-all for arguments you want to pass
                        through to your script. any unfamiliar arguments will
                        just pass right through.
```

## Contributing

To start submitting pull requests to caliban,

First run this:

```sh
f=`git rev-parse --git-dir`/hooks/commit-msg ; mkdir -p $(dirname $f) ; curl -Lo $f https://gerrit-review.googlesource.com/tools/hooks/commit-msg ; chmod +x $f
```

- create a branch
- work!
- commit
- Run the following command:

```bash
git push origin HEAD:refs/for/master
```

More info to file on the process: https://www.gerritcodereview.com/user-review-ui.html

And info from internally on how code review works: https://g3doc.corp.google.com/company/teams/gerritcodereview/users/intro-codelab.md?cl=head#create-a-change

To develop locally, if you have the [Blueshift internal repo](https://team.git.corp.google.com/blueshift/blueshift/) installed, simply run:

```bash
pipx_local caliban
```

in the checked-out Caliban repository. Otherwise, run the following:

```bash
pipx install -e --spec . caliban --force
```

This will allow you to edit the source in your checked-out copy and have it get
picked up by the global alias.


## Testing

This is how to configure tests: https://g3doc.corp.google.com/devtools/kokoro/g3doc/userdocs/general/gob_scm.md?cl=head

## Releasing

We use [versioneer](https://github.com/warner/python-versioneer) for project
versioning. You don't need to do anything with versioneer, as it's already
installed... but for reference, to install it, run:

```bash
pipx install versioneer
```

This links up versioning with git tags. All you need to do now to create a new
version is to run the following in the master branch, when it's time to release:

```bash
git tag 1.0
git push; git push --tags
```

# Trouble?

Get in touch with samritchie@google.com.
