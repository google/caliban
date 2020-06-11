# Caliban

[![Build status](https://img.shields.io/travis/google/caliban/master.svg?maxAge=3600)](http://travis-ci.org/google/caliban)
[![Codecov branch](https://img.shields.io/codecov/c/github/google/caliban/master.svg?maxAge=3600)](https://codecov.io/github/google/Latest)
[![readthedocs](https://img.shields.io/readthedocs/caliban?maxAge=3600)](https://caliban.readthedocs.io/en/latest/?badge=latest)
[![caliban version](https://img.shields.io/pypi/v/caliban?maxAge=3600)](https://pypi.org/project/caliban)

## Overview

Caliban is a tool for developing research workflow and notebooks in an isolated
Docker environment and submitting those isolated environments to Google Compute
Cloud.

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

## Installation and Usage

Caliban lives on [PyPI](https://pypi.org/project/caliban/), so installation is
as easy as:

```bash
pip install -U caliban
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
