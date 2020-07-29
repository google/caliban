# UV + MLFlow Tutorial [ALPHA!]

This directory contains a demo of a model training workflow that uses the
[uv-metrics](https://github.com/google/uv-metrics) library to persist metrics to
an [MLFlow](https://mlflow.org/) tracking server.

This is mostly here for testing and reference. Check back for a documentation
update once the API settles down.

## Setting up MLFLow

You can't install `mlflow` using `pipx`. Here are the steps required to get the
UI running locally.

In a new tab:

- create a new virtualenv, or activate some existing one. It doesn't really
  matter which one, since you only need this for the `mlflow ui` command, not
  your actual code.
- `pip install mlflow`
- Run `mlflow ui` in the `caliban/tutorials/uv-metrics` directory

The UI is now running. Visit http://127.0.0.1:5000/#/ to take a look.

## Running a Job

In the Caliban repository:

```
git checkout aslone/mlflow_tracking && git pull
cd tutorials/uv-metrics
```

Run a single job:

```
caliban run --nogpu trainer.train
```

Name the experiment group and run 3:

```
caliban run --experiment_config experiment.json --xgroup mlflow_tutorial --nogpu trainer.train
```

## Check the MLFlow UI

You may need to refresh, but the UI should now show multiple experiments.

All of the data is stored in the local directory, in the `mlruns` folder; so you
can run a bunch of experiments and pre-stage data if you like, then launch the
UI and have it all still there.
