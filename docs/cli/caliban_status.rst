caliban status
^^^^^^^^^^^^^^^^^^^^^^

The ``caliban status`` command allows you to check on the status of jobs submitted
via caliban. There are two primary modes for this command. The first returns
your most recent job submissions across all experiment groups:

.. code-block::

   $ caliban status --max_jobs 5
   most recent 5 jobs for user totoro:

   xgroup totoro-xgroup-2020-05-28-11-33-35:
     docker config 1: job_mode: CPU, build url: ~/sw/cluster/caliban/tmp/cpu, extra dirs: None
      experiment id 28: cpu.py --foo 3 --sleep 2
        job 56       STOPPED        GKE 2020-05-28 11:33:35 container: gcr.io/totoro-project/0f6d8a3ddbee:latest name: job-stop-test-rssqq
      experiment id 29: cpu.py --foo 3 --sleep 600
        job 57       STOPPED        GKE 2020-05-28 11:33:36 container: gcr.io/totoro-project/0f6d8a3ddbee:latest name: job-stop-test-c5x6v

   xgroup totoro-xgroup-2020-05-28-11-40-52:
     docker config 1: job_mode: CPU, build url: ~/sw/cluster/caliban/tmp/cpu, extra dirs: None
       experiment id 30: cpu.py --foo 3 --sleep -1
         job 58       STOPPED       CAIP 2020-05-28 11:40:54 container: gcr.io/totoro-project/0f6d8a3ddbee:latest name: caliban_totoro_20200528_114052_1
       experiment id 31: cpu.py --foo 3 --sleep 2
         job 59       STOPPED       CAIP 2020-05-28 11:40:55 container: gcr.io/totoro-project/0f6d8a3ddbee:latest name: caliban_totoro_20200528_114054_2
       experiment id 32: cpu.py --foo 3 --sleep 600
         job 60       RUNNING       CAIP 2020-05-28 11:40:56 container: gcr.io/totoro-project/0f6d8a3ddbee:latest name: caliban_totoro_20200528_114055_3

Here we can see five jobs that we recently submitted, in two experiment groups.
The first experiment group has jobs submitted to GKE, while the second has jobs
submitted to CAIP. You can specify the maximum number of jobs to return using
the ``--max_jobs`` flag.

The second mode for the ``caliban status`` command returns jobs in a given
experiment group, using the ``--xgroup`` flag:

.. code-block::

   $ caliban status --xgroup xg2 --max_jobs 2
   xgroup xg2:
   docker config 1: job_mode: CPU, build url: ~/sw/cluster/caliban/tmp/cpu, extra dirs: None
     experiment id 1: cpu.py --foo 3 --sleep -1
       job 34       FAILED        CAIP 2020-05-08 18:26:56 container: gcr.io/totoro-project/e2a0b8fca1dc:latest name: caliban_totoro_1_20200508_182654
       job 37       FAILED        CAIP 2020-05-08 19:01:08 container: gcr.io/totoro-project/e2a0b8fca1dc:latest name: caliban_totoro_1_20200508_190107
     experiment id 2: cpu.py --foo 3 --sleep 2
       job 30       SUCCEEDED    LOCAL 2020-05-08 09:59:04 container: e2a0b8fca1dc
       job 35       SUCCEEDED     CAIP 2020-05-08 18:26:57 container: gcr.io/totoro-project/e2a0b8fca1dc:latest name: caliban_totoro_2_20200508_182656
     experiment id 5: cpu.py --foo 3 --sleep 600
       job 36       STOPPED       CAIP 2020-05-08 18:26:58 container: gcr.io/totoro-project/e2a0b8fca1dc:latest name: caliban_totoro_3_20200508_182657
       job 38       SUCCEEDED     CAIP 2020-05-08 19:01:09 container: gcr.io/totoro-project/e2a0b8fca1dc:latest name: caliban_totoro_3_20200508_190108

Here we can see the jobs that have been submitted as part of the ``xg2``
experiment group. By specifying ``--max_jobs 2`` in the call, we can see the two
most recent job submissions for each experiment in the group. In this case, we
can see that experiment 2 was submitted both locally and to CAIP at different
times. We can also see that experiment 1 failed (due to an invalid parameter),
and that the first submision to CAIP of experiment 5 was stopped by the user.

Another interesting thing to note here is that the container hash is the same
for each of these job submissions, so we can tell that the underlying code did
not change between submissions.

This command supports the following arguments:

.. code-block::

   $ caliban status --help
   usage: caliban status [-h] [--helpfull] [--xgroup XGROUP]
                         [--max_jobs MAX_JOBS]

   optional arguments:
     -h, --help           show this help message and exit
     --helpfull           show full help message and exit
     --xgroup XGROUP      experiment group
     --max_jobs MAX_JOBS  Maximum number of jobs to view. If you specify an
                          experiment group, then this specifies the maximum
                          number of jobs per experiment to view. If you do not
                          specify an experiment group, then this specifies the
                          total number of jobs to return, ordered by creation
                          date, or all jobs if max_jobs==0.
