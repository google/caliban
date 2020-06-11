caliban resubmit
^^^^^^^^^^^^^^^^^^^^^^^^

Often one needs to re-run an experiment after making code changes, or to run the
same code with a different random seed. Caliban supports this with its
``resubmit`` command.

This command allows you to resubmit jobs in an experiment group without having
to remember or re-enter all of the parameters for your experiments. For example,
suppose you run a set of experiments in an experiment group on CAIP:

.. code-block::

   caliban cloud --xgroup resubmit_test --nogpu --experiment_config experiment.json cpu.py -- --foo 3

You then realize that you made a coding error, causing some of your jobs to
fail:

.. code-block::

   $ caliban status --xgroup resubmit_test
   xgroup resubmit_test:
   docker config 1: job_mode: CPU, build url: ~/sw/cluster/caliban/tmp/cpu, extra dirs: None
     experiment id 37: cpu.py --foo 3 --sleep 2
       job 69       SUCCEEDED     CAIP 2020-05-29 10:53:41 container: gcr.io/totoro-project/cffd1475aaca:latest name: caliban_totoro_20200529_105340_2
     experiment id 38: cpu.py --foo 3 --sleep 1
       job 68       FAILED        CAIP 2020-05-29 10:53:40 container: gcr.io/totoro-project/cffd1475aaca:latest name: caliban_totoro_20200529_105338_1

You then go and modify your code, and now you can use the ``resubmit`` command to
run the jobs that failed:

.. code-block::

   $ caliban resubmit --xgroup resubmit_test
   the following jobs would be resubmitted:
   cpu.py --foo 3 --sleep 1
     job 68       FAILED        CAIP 2020-05-29 10:53:40 container: gcr.io/totoro-project/cffd1475aaca:latest name: caliban_totoro_20200529_105338_1

    do you wish to resubmit these 1 jobs? [yN]: y
   rebuilding containers...
   ...
   Submitting request!
   ...

Checking back in with ``caliban status`` shows that the code change worked, and
now all of the experiments in the group have succeeded, and you can see that the
container hash has changed for the previously failed jobs, reflecting your code
change:

.. code-block::

   $ caliban status --xgroup resubmit_test
   xgroup resubmit_test:
   docker config 1: job_mode: CPU, build url: ~/sw/cluster/caliban/tmp/cpu, extra dirs: None
     experiment id 37: cpu.py --foo 3 --sleep 2
       job 69       SUCCEEDED     CAIP 2020-05-29 10:53:41 container: gcr.io/totoro-project/cffd1475aaca:latest name: caliban_totoro_20200529_105340_2
     experiment id 38: cpu.py --foo 3 --sleep 1
       job 70       SUCCEEDED     CAIP 2020-05-29 11:03:01 container: gcr.io/totoro-project/81b2087b5026:latest name: caliban_totoro_20200529_110259_1

The ``resubmit`` command supports the following arguments:

.. code-block::

   $ caliban resubmit --help
   usage: caliban resubmit [-h] [--helpfull] [--xgroup XGROUP] [--dry_run] [--all_jobs] [--project_id PROJECT_ID] [--cloud_key CLOUD_KEY]

   optional arguments:
     -h, --help            show this help message and exit
     --helpfull            show full help message and exit
     --xgroup XGROUP       experiment group
     --dry_run             Don't actually submit; log everything that's going to happen.
     --all_jobs            resubmit all jobs regardless of current state, otherwise only jobs that are in FAILED or STOPPED state will be resubmitted
     --project_id PROJECT_ID
                           ID of the GCloud AI Platform/GKE project to use for Cloud job submission and image persistence. (Defaults to $PROJECT_ID; errors if both the argument and $PROJECT_ID are empty.)
     --cloud_key CLOUD_KEY
                           Path to GCloud service account key. (Defaults to $GOOGLE_APPLICATION_CREDENTIALS.)
