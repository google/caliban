# UV + MLFlow Tutorial [ALPHA!]

This directory contains a demo of a model training workflow that uses the
[uv-metrics](https://github.com/google/uv-metrics) library to persist metrics to
an [MLFlow](https://mlflow.org/) tracking server.

This is mostly here for testing and reference. Check back for a documentation
update once the API settles down.

## Prerequisites

Right now we are supporting logging metrics to a sql-based backing store only
in this tutorial, but we will update things to allow for local storage in the
future. For now you will need to have a google cloud sql instance configured
for this, and you will need an MLFlow server set up to serve results from
this instance.

To run this tutorial, you will need to edit the `.calibanconfig.json`
file in this directory to reflect your database settings so that the training
script can connect to the database and log metrics. The specific entries to
edit here are in the `mflow_config` entry in `.calibanconfig.json`:

```
{
  "apt_packages" : ["openssh-client", "curl"],
  "mlflow_config" : {"project": <your gcp project where your cloudsql db lives>,
                     "region": <the region where your database lives>,
                     "db": <the name of your mlflow database>,
                     "user": <connect as this database user>,
                     "password": <the database password for the above user>,
                     "artifact_root": <the location to store artifacts, typically a gs bucket>,
                     "debug" : false}
}
```

One note here is that currently artifact storage is not working completely, but
please specify this entry and we will update this tutorial once that is working properly.

Once you have set these parameters properly, you should be able to run the tutorial code.

## Sanity Check (optional)

A quick sanity check to test your database connection is to set the `debug` flag in
the `.calibanconfig.json` file to `true`, and then use Caliban to run the `hello_world.sh`
script. This script simply prints "hello, world", but by enabling the `debug` flag, we
can check the status of the database connection.

To run this test:

```
caliban run --nogpu hello_world.sh
```

If your database settings are configured properly, you should see output like the following:

```
Successfully built 5eb8dcef14ce
I0807 13:02:53.008464 139963939288896 tqdm.py:90] Restoring pure python logging
I0807 13:02:53.010536 139963939288896 run.py:74]
I0807 13:02:53.010816 139963939288896 run.py:75] Job 1 - Experiment args: []
I0807 13:02:53.010974 139963939288896 run.py:198] Running command: docker run --ipc host -e PYTHONUNBUFFERED=1 -e COLUMNS=211 -e LINES=19 5eb8dcef14ce ...
2020/08/07 20:02:53 current FDs rlimit set to 1048576, wanted limit is 8500. Nothing to do here.
2020/08/07 20:02:53 using credential file for authentication; path="/home/<username>/.config/gcloud/application_default_credentials.json"
2020/08/07 20:02:54 Listening on /tmp/cloudsql/<project>:<region>:<db>/.s.PGSQL.5432 for <project>:<region>:<db>
2020/08/07 20:02:54 Ready for new connections
INFO:root:/bin/bash hello_world.sh
hello, world
I0807 13:03:04.015075 139963939288896 run.py:111] Job 1 succeeded!
```

As long as you see `Ready for new connections`, then your configuration should be ok, and you
can disable the `debug` flag and continue with the rest of the tutorial.

## Running a Job

In the Caliban repository:

```
git checkout master && git pull
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

You may need to refresh, but the UI should now show multiple experiments. You can view the
status and metrics for your jobs from the UI while your jobs are in progress, which is
useful for long-running jobs.
