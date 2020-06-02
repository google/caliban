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

## Installation and Usage

We'll add more here once we're staged on Github and can get proper links to
generated docs.

This is a research project, not an official Google product. Expect bugs and
sharp edges. Please help by trying out Caliban, [reporting
bugs](https://github.com/google/caliban/issues), and letting us know what you
think!

## Developing in Caliban

So you want to add some code to Caliban. Excellent!

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

## Publishing Caliban

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
