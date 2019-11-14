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
Docker environment and submitting docker containers to the Cloud.

## Prerequisites

Before you can install and use Caliban to manage your research workflows, you'll
need a solid Cloud and Docker installation. Follow these steps to get set up:

### Python 3

Make sure your `python3` is up to date by running the following command at your workstation:

```bash
sudo apt-get install python3 python3-venv python3-pip
```

If you're on a Mac, download [Python 3.7.5 from
python.org](https://www.python.org/downloads/mac-osx) ([direct download
link](https://www.python.org/ftp/python/3.7.5/python-3.7.5-macosx10.9.pkg))

Once that's all set, verify that you're running python 3.7 or above:

```bash
$ python3 --version
Python 3.7.5
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

### Docker and CUDA

You need Docker on your machine. Use Blueshift's [Working with
Docker](https://g3doc.corp.google.com/company/teams/blueshift/guide/docker.md?cl=head)
tutorial to get yourself set up, also found at https://go/blueshift-dev.

If you're on a Mac laptop, install [Docker Desktop for
Mac](https://docs.docker.com/docker-for-mac/install/) (so easy!)

If you're on a workstation, you'll need to make sure that your CUDA drivers are
up to date, and that you have a big-iron GPU installed in your workstation. The
[Workstation GPU
installation](https://g3doc.corp.google.com/company/teams/blueshift/guide/gpu_install.md?cl=head)
tutorial will get you sorted.

## Getting Caliban

If you've already installed the [Blueshift internal
repository](https://team.git.corp.google.com/blueshift/blueshift/), the easiest
way to get Caliban is to run the following in your terminal (make sure you don't
have a virtualenv activated when you run this!):

```bash
install_caliban
```

This command will install the `caliban` command into its own isolated virtual
environment and make the command globally available.

### Manual Installation

If you don't have the Blueshift repo installed, or if the above is failing, here are the steps, written out more exhaustively.

First, install `pipx`:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

`pipx` is a tool that lets you install command line utilities written in Python
into their own virtual environments, completely isolated from your system python
packages or other virtualenvs.

Once `pipx` is installed, use it to install `caliban`:

```bash
pipx install -e --spec git+sso://team/blueshift/caliban caliban
```

### Check your Installation

To check if all is well, run

```bash
caliban --help
```

to see the list of subcommands. We'll explore the meaning of each below.

## Using Caliban

If you want to practice using Caliban with a proper getting-started style guide,
head over to Blueshift's [Hello
World](https://team.git.corp.google.com/blueshift/hello-world/) repository.

Read on for information on the specific commands exposed by Caliban.

### caliban shell

Running `caliban shell` in any directory will create a docker container totally

### caliban notebook

### caliban run

### caliban cloud

Configure your machine for Cloud access using the tutorial at Blueshift's
[Setting up
Cloud](https://g3doc.corp.google.com/company/teams/blueshift/guide/cloud.md?cl=head)
page.

## Contributing

To push code,

First run this:

```sh
f=`git rev-parse --git-dir`/hooks/commit-msg ; mkdir -p $(dirname $f) ; curl -Lo $f https://gerrit-review.googlesource.com/tools/hooks/commit-msg ; chmod +x $f
```

- create a branch
- work!
- commit
- `git push origin HEAD:refs/for/master`

More info to file on the process: https://www.gerritcodereview.com/user-review-ui.html

And info from internally on how code review works: https://g3doc.corp.google.com/company/teams/gerritcodereview/users/intro-codelab.md?cl=head#create-a-change

Then to develop locally, reinstall Caliban like this from the project directory:

```bash
pipx install -e --spec . caliban --force
```

This will allow you to edit the source in your checked-out copy and have it get
picked up by the global alias.


## Testing

This is how to configure tests.

https://g3doc.corp.google.com/devtools/kokoro/g3doc/userdocs/general/gob_scm.md?cl=head

# Trouble?

Get in touch with samritchie@google.com.
