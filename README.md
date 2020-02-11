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

in the parent of the checked-out Caliban repository. Otherwise, run the
following in the parent of the Caliban directory:

```bash
pipx install -e --force caliban
```

This will allow you to edit the source in your checked-out copy and have it get
picked up by the global alias.


## Pre-Commit Hooks

We use https://github.com/pre-commit/pre-commit to manage pre-commit hooks. To install these, run:

```bash
pipx install pre-commit
```

Then install all the hooks with:

```bash
pre-commit install
```

To test out the hooks, run:

```bash
pre-commit run --all-files
```


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
