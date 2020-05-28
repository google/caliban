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

All documentation for how to install and interact with Caliban lives at
<https://go/caliban>.

If you want to get started in a more interactive way, head over to
<https://go/bs-tutorials>.


## Installing Caliban

The [Installing Caliban](http://go/caliban#getting-caliban) section of Caliban's
[g3doc documentation](http://go/caliban#getting-caliban) describes at length how
to install Caliban on your laptop, workstation or a Cloud VM. Head [to those
docs](http://go/caliban#getting-caliban) for the full story.


## Developing in Caliban

So you want to add some code to Caliban. Excellent!

### Checkout and pre-commit hooks

First, check out the repo:

```
git clone sso://team/blueshift/caliban && cd caliban
```

Then run this command to install a special pre-commit hook that Gerrit needs to
manage code review properly. You'll only have to run this once.

```bash
f=`git rev-parse --git-dir`/hooks/commit-msg ; mkdir -p $(dirname $f) ; curl -Lo $f https://gerrit-review.googlesource.com/tools/hooks/commit-msg ; chmod +x $f
```

We use [pre-commit](https://pre-commit.com/) to manage a series of git
pre-commit hooks for the project; for example, each time you commit code, the
hooks will make sure that your python is formatted properly. If your code isn't,
the hook will format it, so when you try to commit the second time you'll get
past the hook.

All hooks are defined in `.pre-commit-config.yaml`. To install these hooks,
install `pre-commit` if you don't yet have it. I prefer using
[pipx](https://github.com/pipxproject/pipx) so that `pre-commit` stays globally
available.

```bash
pipx install pre-commit
```

Then install the hooks with this command:

```bash
pre-commit install
```

Now they'll run on every commit. If you want to run them manually, you can run either of these commands:

```bash
pre-commit run --all-files

# or this, if you've previously run `make build`:
make lint
```

### Developing Interactively

It's quite nice to develop against a local installation that live-updates
whenever you modify the checked out code. If you have the [Blueshift internal
repo](https://team.git.corp.google.com/blueshift/blueshift/) installed, simply
run:

```bash
pipx_local caliban
```

in the parent directory of the checked-out Caliban repository. Otherwise, run
the following in the parent of the Caliban directory:

```bash
pipx install -e --force caliban
```

This will allow you to edit the source in your checked-out copy and have it get
picked up by the global alias.

### Aliases

You might find these aliases helpful when developing in Caliban:

```
[alias]
	review = "!f() { git push origin HEAD:refs/for/${1:-master}; }; f"
	amend  = "!f() { git add . && git commit --amend --no-edit; }; f"
```

### New Feature Workflow

To add a new feature, you'll want to do the following:

- create a new branch off of `master` with `git checkout -b my_branch_name`.
  Don't push this branch yet!
- run `make build` to set up a virtual environment inside the current directory.
- periodically run `make pytest` to check that your modifications pass tests.
- to run a single test file, run the following command:

```bash
env/bin/pytest tests/path/to/your/test.py
```

You can always use `env/bin/python` to start an interpreter with the correct
dependencies for the project.

When you're ready for review,

- commit your code to the branch (multiple commits are fine)
- run `git review` in the terminal. (This is equivalent to running `git push
  origin HEAD:refs/for/master`, but way easier to remember.)

The link to your pull request will show up in the terminal.

If you need to make changes to the pull request, navigate to the review page and
click the "Download" link at the bottom right:

![](https://screenshot.googleplex.com/4BP8v3TWq4R.png)

Copy the "checkout" code, which will look something like this:

```bash
git fetch "sso://team/blueshift/caliban" refs/changes/87/670987/2 && git checkout FETCH_HEAD
```

And run that in your terminal. This will get you to a checkout with all of your
code. Make your changes, then run `git amend && git review` to modify the pull
request and push it back up. (Remember, these are aliases we declared above.)

## Publishing Caliban

Caliban is typically installed from Git-on-Borg or its Cloud Source Repository
mirror, as described in the [Getting Caliban](go/caliban#getting-caliban)
documentation.

- First, run `make build` to get your virtual environment set up.
- Make sure that you're on the master branch!
- add a new tag, with `git tag 0.2.3` or the equivalent
- run `make release` to push the latest code and tags to all relevant
  repositories.

## Citing Caliban

To cite this repository:

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
