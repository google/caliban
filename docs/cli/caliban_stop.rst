caliban stop
^^^^^^^^^^^^^^^^^^^^

This command allows you to stop running jobs submitted using caliban.

For example, suppose you submit a group of experiments to GKE using an
experiment config file like the following:

.. code-block::

   $ caliban cluster job submit --xgroup my-xgroup ... --experiment_config exp.json cpu.py --

After a bit, you realize that you made a coding error, so you'd like to stop
these jobs so that you can fix your error without wasting cloud resources (and
money). The ``caliban stop`` command makes this relatively simple:

.. code-block::

   $ caliban stop --xgroup my-xgroup
   the following jobs would be stopped:
   cpu.py --foo 3 --sleep -1
       job 61       RUNNING        GKE 2020-05-28 11:55:04 container: gcr.io/totoro-project/0f6d8a3ddbee:latest name: job-stop-test-57pr9
   cpu.py --foo 3 --sleep 2
       job 62       RUNNING        GKE 2020-05-28 11:55:04 container: gcr.io/totoro-project/0f6d8a3ddbee:latest name: job-stop-test-s67jt
   cpu.py --foo 3 --sleep 600
       job 63       RUNNING        GKE 2020-05-28 11:55:04 container: gcr.io/totoro-project/0f6d8a3ddbee:latest name: job-stop-test-gg9zm

   do you wish to stop these 3 jobs? [yN]: y

   stopping job: 61       RUNNING        GKE 2020-05-28 11:55:04 container: gcr.io/totoro-project/0f6d8a3ddbee:latest name: job-stop-test-57pr9
   stopping job: 62       RUNNING        GKE 2020-05-28 11:55:04 container: gcr.io/totoro-project/0f6d8a3ddbee:latest name: job-stop-test-s67jt
   stopping job: 63       RUNNING        GKE 2020-05-28 11:55:04 container: gcr.io/totoro-project/0f6d8a3ddbee:latest name: job-stop-test-gg9zm

   requested job cancellation, please be patient as it may take a short while for this status change to be reflected in the gcp dashboard or from the `caliban status` command.

This command will stop all jobs that are in a ``RUNNING`` or ``SUBMITTED`` state,
and checks with you to make sure this is what you *really* intend, as
accidentally stopping a job that has been running for days is a particularly
painful experience if your checkpointing is less than perfect. Similar to other
caliban commands, you can use the ``--dry_run`` flag to just print what jobs would
be stopped.

This command supports the following arguments:

.. code-block::

   $ caliban stop --help
   usage: caliban stop [-h] [--helpfull] [--xgroup XGROUP] [--dry_run]

   optional arguments:
     -h, --help       show this help message and exit
     --helpfull       show full help message and exit
     --xgroup XGROUP  experiment group
     --dry_run        Don't actually submit; log everything that's going to
                      happen.
