# How to Contribute

So you want to add some code to Caliban. Excellent!

Pull requests and bug reports are always welcome! Check out our [Contributor's
Guide](CONTRIBUTING.md) for information on how to get started contributing to
Caliban.

The TL;DR; is:

- send us a pull request,
- iterate on the feedback + discussion, and
- get a +1 from a [Committer](COMMITTERS.md)

in order to get your PR accepted.

Issues should be reported on the [GitHub issue
tracker](https://github.com/google/caliban/issues).

If you want to discuss an idea for a new feature or ask us a question,
discussion occurs primarily in the body of [Github
Issues](https://github.com/google/caliban/issues), though the project is growing
large enough that we may start a Gitter channel soon.

The current list of active committers (who can +1 a pull request) can be found
here: [COMMITTERS.md](COMMITTERS.md)

A list of contributors to the project can be found at the project's
[Contributors](https://github.com/google/caliban/graphs/contributors) page.

## Contributor License Agreement

Contributions to this project must be accompanied by a Contributor License
Agreement. You (or your employer) retain the copyright to your contribution;
this simply gives us permission to use and redistribute your contributions as
part of the project. Head over to <https://cla.developers.google.com/> to see
your current agreements on file or to sign a new one.

You generally only need to submit a CLA once, so if you've already submitted one
(even if it was for a different project), you probably don't need to do it
again.

## Developing in Caliban

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

## Documentation

We use Sphinx to generate docs. If you want to live-preview your changes to the
documentation as you are editing, you can use
[sphinx-reload](https://pypi.org/project/sphinx-reload/). To get this working:

```bash
pipx install sphinx-reload
```

Then, inside the caliban folder:

```bash
make build
sphinx-reload docs
```

If all goes well, `sphinx-reload` will tell you it is serving the documentation
on a port, which you can listen into from your browser.

## Publishing Caliban

- First, run `make build` to get your virtual environment set up.
- Make sure that you're on the master branch!
- add a new tag, with `git tag 0.2.3` or the equivalent
- run `make release` to push the latest code and tags to all relevant
  repositories.
