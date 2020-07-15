# UV + MLFlow Tutorial

## Get the custom Caliban build installed

This is simple:

```
install_caliban aslone/mlflow_tracking
```

## Setting up MLFLow

Annoyingly, you can't install `mlflow` using pipx. Here are the steps required
to get the UI running locally.

In a new tab:

- create a new virtualenv, or activate some existing one. It doesn't really
  matter which one, since you only need this for the `mlflow ui` command, not
  your actual code.
- `pip install mlflow`
- Run `mlflow ui` in the `caliban/tutorials/uv-metrics` directory

The UI is now running. Visit http://127.0.0.1:5000/#/ to take a look.

## Running a Job

In the caliban repo:

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
caliban run --experiment_config experiment.json --xgroup guy_research --nogpu trainer.train
```

## Check the MLFlow UI

You may need to refresh, but the UI should now show multiple experiments.

All of the data is stored in the local directory, in the `mlruns` folder; so you
can run a bunch of experiments and pre-stage data if you like, then launch the
UI and have it all still there.
