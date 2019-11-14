# Caliban

![](https://upload.wikimedia.org/wikipedia/commons/a/ad/Stephano%2C_Trinculo_and_Caliban_dancing_from_The_Tempest_by_Johann_Heinrich_Ramberg.jpg)

> “Be not afeard; the isle is full of noises, Sounds, and sweet airs, that give
> delight and hurt not. Sometimes a thousand twangling instruments Will hum
> about mine ears; and sometime voices, That, if I then had waked after long
> sleep, Will make me sleep again: and then, in dreaming, The clouds methought
> would open, and show riches Ready to drop upon me; that, when I waked, I cried
> to dream again.”
>
> -- <cite>Shakespeare, The Tempest</cite>

## Overview

Caliban is a tool for running python code inside of Docker containers, then
submitting those containers up to Cloud.

## Prerequisites

Before you can install and use Caliban to manage your research workflows, you'll
need a solid Cloud and Docker installation. Follow these steps to get set up:

-   Configure your machine for Cloud access using the tutorial at Blueshift's
    [Setting up Cloud](https://g3doc.corp.google.com/company/teams/blueshift/guide/cloud.md?cl=head)
    page.
-   You need Docker on your machine. Use Blueshift's
    [Working with Docker](https://g3doc.corp.google.com/company/teams/blueshift/guide/docker.md?cl=head)
    tutorial, also found at https://go/blueshift-dev.
-   If you want to run the tutorial in GPU mode, you'll need to make sure your
    CUDA drivers are up to date, and that you have a big-iron GPU installed in
    your workstation. The
    [Workstation GPU installation](https://g3doc.corp.google.com/company/teams/blueshift/guide/gpu_install.md?cl=head)
    tutorial will get you sorted.

Once that's all set, verify that you're running python 3.7 or above:

```bash
$ python3 --version
Python 3.7.3
```

## Getting Caliban

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

## Using Caliban

If you want to practice using Caliban with a proper getting-started style guide,
head over to Blueshift's
[Hello World](https://team.git.corp.google.com/blueshift/hello-world/)
repository.

Read on for information on the specific commands exposed by Caliban.

### caliban notebook

### caliban shell

### caliban run

### caliban cloud

## Contributing

To push code,

First run this:

```sh
f=`git rev-parse --git-dir`/hooks/commit-msg ; mkdir -p $(dirname $f) ; curl -Lo $f https://gerrit-review.googlesource.com/tools/hooks/commit-msg ; chmod +x $f
```

-   create a branch
-   work!
-   commit
-   `git push origin HEAD:refs/for/master`

More info to file on the process:
https://www.gerritcodereview.com/user-review-ui.html

And info from internally on how code review works:
https://g3doc.corp.google.com/company/teams/gerritcodereview/users/intro-codelab.md?cl=head#create-a-change

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
