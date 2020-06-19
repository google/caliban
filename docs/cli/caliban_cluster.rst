caliban cluster
^^^^^^^^^^^^^^^

This subcommand allows you to create and submit jobs to a GKE cluster using
caliban's packaging and interface features.

``caliban cluster ls``
~~~~~~~~~~~~~~~~~~~~~~~~~~

This command lists the clusters currently available in your project.

.. code-block:: text

   usage: caliban cluster ls [-h] [--helpfull] [--project_id PROJECT_ID]
                             [--cloud_key CLOUD_KEY] [--zone ZONE]

   list clusters

   optional arguments:
     -h, --help            show this help message and exit
     --helpfull            show full help message and exit
     --project_id PROJECT_ID
                           ID of the GCloud AI Platform/GKE project to use for
                           Cloud job submission and image persistence. (Defaults
                           to $PROJECT_ID; errors if both the argument and
                           $PROJECT_ID are empty.) (default: None)
     --cloud_key CLOUD_KEY
                           Path to GCloud service account key. (Defaults to
                           $GOOGLE_APPLICATION_CREDENTIALS.) (default: None)
     --zone ZONE           zone (default: None)

Here you may specify a specific project, credentials file, or cloud zone to
narrow your listing. If you do not specify these, caliban tries to determine
these from the system defaults.

``caliban cluster create``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This command creates a new cluster in your project. Typically if you are going
to use GKE in your project, you will create a single long-running cluster in
your project first, and leave it running across many job submissions. In caliban
we configure the cluster to take advantage of autoscaling wherever possible.

In GKE, there are two types of autoscaling. The first is known as
`'cluster autoscaling' <https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-autoscaler>`_.
This mode automatically increases the number of nodes in your cluster's node
pools as job demand increases. In caliban, we configure this automatically and
we query your cpu and accelerator quota to configure the cluster autoscaling
limits. In this way, your cluster will automatically add nodes when you need
them, and then automatically delete them when they are no longer needed. This
is, of course, quite useful for keeping your costs low.

The second type of autoscaling in GKE is
`'node autoprovisioning' <https://cloud.google.com/kubernetes-engine/docs/how-to/node-auto-provisioning>`_.
This form of autoprovisioning addresses the issue that accelerator-enabled
instances must be allocated from a node pool of instances where the particular
cpu/memory/gpu configuration is fixed. For simple configurations where you
support only a small number of node configurations, you can manually create
autoscaling node pools. If, however, you wish to support several, or in
caliban's case, general, configurations, then this becomes more difficult. Node
autoprovisioning automatically creates autoscaling node pools based on the
requirements of the jobs submitted to the cluster, and also deletes these node
pools once they are no longer needed. In caliban we enable node autoprovisioning
so you can specify your gpu- and machine- types on a per-job basis, and the
kubernetes engine will automatically create the appropriate node pools to
accomodate your jobs.

The syntax for this command is as follows:

.. code-block:: text

   totoro@totoro:$ caliban cluster create --help
   usage: caliban cluster create [-h] [--helpfull] [--project_id PROJECT_ID]
                                 [--cloud_key CLOUD_KEY]
                                 [--cluster_name CLUSTER_NAME] [--zone ZONE]
                                 [--dry_run]
                                 [--release_channel ['UNSPECIFIED', 'RAPID', 'REGULAR', 'STABLE']]
                                 [--single_zone]

   create cluster

   optional arguments:
     -h, --help            show this help message and exit
     --helpfull            show full help message and exit
     --project_id PROJECT_ID
                           ID of the GCloud AI Platform/GKE project to use for
                           Cloud job submission and image persistence. (Defaults
                           to $PROJECT_ID; errors if both the argument and
                           $PROJECT_ID are empty.) (default: None)
     --cloud_key CLOUD_KEY
                           Path to GCloud service account key. (Defaults to
                           $GOOGLE_APPLICATION_CREDENTIALS.) (default: None)
     --cluster_name CLUSTER_NAME
                           cluster name (default: None)
     --zone ZONE           for a single-zone cluster, this specifies the zone for
                           the cluster control plane and all worker nodes, while
                           for a multi-zone cluster this specifies only the zone
                           for the control plane, while worker nodes may be
                           created in any zone within the same region as the
                           control plane. The single_zone argument specifies
                           whether to create a single- or multi- zone cluster.
                           (default: None)
     --dry_run             Don't actually submit; log everything that's going to
                           happen. (default: False)
     --release_channel ['UNSPECIFIED', 'RAPID', 'REGULAR', 'STABLE']
                           cluster release channel, see
                           https://cloud.google.com/kubernetes-
                           engine/docs/concepts/release-channels (default: REGULAR)
     --single_zone         create a single-zone cluster if set, otherwise create
                           a multi-zone cluster: see
                           https://cloud.google.com/kubernetes-
                           engine/docs/concepts/types-of-
                           clusters#cluster_availability_choices (default: False)

You can use the ``--dry_run`` flag to see the specification for the cluster that
would be submitted to GKE without actually creating the cluster.

A typical creation request (with ``--dry_run``\ ):

.. code-block:: text

   totoro@totoro:$ caliban cluster create --zone us-central1-a --cluster_name newcluster --dry_run
   I0303 13:07:34.257717 140660011796288 cli.py:160] request:
   {'cluster': {'autoscaling': {'autoprovisioningNodePoolDefaults': {'oauthScopes': ['https://www.googleapis.com/auth/compute',
                                                                                     'https://www.googleapis.com/auth/cloud-platform']},
                                'enableNodeAutoprovisioning': 'true',
                                'resourceLimits': [{'maximum': '72',
                                                    'resourceType': 'cpu'},
                                                   {'maximum': '4608',
                                                    'resourceType': 'memory'},
                                                   {'maximum': '8',
                                                    'resourceType': 'nvidia-tesla-k80'},
                                                   {'maximum': '1',
                                                    'resourceType': 'nvidia-tesla-p100'},
                                                   {'maximum': '1',
                                                    'resourceType': 'nvidia-tesla-v100'},
                                                   {'maximum': '1',
                                                    'resourceType': 'nvidia-tesla-p4'},
                                                   {'maximum': '4',
                                                    'resourceType': 'nvidia-tesla-t4'}]},
                'enable_tpu': 'true',
                'ipAllocationPolicy': {'useIpAliases': 'true'},
                'locations': ['us-central1-a',
                              'us-central1-b',
                              'us-central1-c',
                              'us-central1-f'],
                'name': 'newcluster',
                'nodePools': [{'config': {'oauthScopes': ['https://www.googleapis.com/auth/devstorage.read_only',
                                                          'https://www.googleapis.com/auth/logging.write',
                                                          'https://www.googleapis.com/auth/monitoring',
                                                          'https://www.googleapis.com/auth/service.management.readonly',
                                                          'https://www.googleapis.com/auth/servicecontrol',
                                                          'https://www.googleapis.com/auth/trace.append']},
                               'initialNodeCount': '3',
                               'name': 'default-pool'}],
                'releaseChannel': {'channel': 'RAPID'},
                'zone': 'us-central1-a'},
    'parent': 'projects/totoro-project/locations/us-central1-a'}

Cluster creation can take a while to complete (often on the order of five
minutes). When you use caliban to create a cluster, caliban will provide a link
to the relevant GCP dashboard page where you can monitor the progress of your
cluster creation request. Caliban will also monitor your creation request, and
when your cluster is created, it will apply a
`daemonset <https://kubernetes.io/docs/concepts/workloads/controllers/daemonset/>`_
to your cluster to automatically apply nvidia drivers to any gpu-enabled nodes
that get created, as described
`here <https://cloud.google.com/kubernetes-engine/docs/how-to/gpus#installing_drivers>`_.

``caliban cluster delete``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This command simply deletes an existing cluster. Typically you will leave your
cluster running, but the cluster does consume some resources even when idle, so
if you are not actively using the cluster you may want to shut it down to save
money.

The syntax of this command:

.. code-block:: text

   totoro@totoro:$ caliban cluster delete --help
   usage: caliban cluster delete [-h] [--helpfull] [--project_id PROJECT_ID]
                                 [--cloud_key CLOUD_KEY]
                                 [--cluster_name CLUSTER_NAME] [--zone ZONE]

   delete cluster

   optional arguments:
     -h, --help            show this help message and exit
     --helpfull            show full help message and exit
     --project_id PROJECT_ID
                           ID of the GCloud AI Platform/GKE project to use for
                           Cloud job submission and image persistence. (Defaults
                           to $PROJECT_ID; errors if both the argument and
                           $PROJECT_ID are empty.) (default: None)
     --cloud_key CLOUD_KEY
                           Path to GCloud service account key. (Defaults to
                           $GOOGLE_APPLICATION_CREDENTIALS.) (default: None)
     --cluster_name CLUSTER_NAME
                           cluster name (default: None)
     --zone ZONE           zone (default: None)

As with most caliban commands, if you do not specify arguments, then caliban
does its best to determine them from defaults. For example, if you have only a
single cluster in your project, you can simply type ``caliban cluster delete``.

``caliban cluster job submit``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Most of the cli arguments for ``caliban cluster job submit`` are the same as
those for :doc:`../cli/caliban_cloud`:

.. code-block:: text

   totoro@totoro:$ caliban cluster job submit --help
   usage: caliban cluster job submit [-h] [--helpfull]
                                  [--cluster_name CLUSTER_NAME] [--nogpu]
                                  [--cloud_key CLOUD_KEY] [--extras EXTRAS]
                                  [-d DIR] [--image_tag IMAGE_TAG]
                                  [--project_id PROJECT_ID]
                                  [--min_cpu MIN_CPU] [--min_mem MIN_MEM]
                                  [--gpu_spec NUMxGPU_TYPE]
                                  [--tpu_spec NUMxTPU_TYPE]
                                  [--tpu_driver TPU_DRIVER]
                                  [--nonpreemptible_tpu] [--force]
                                  [--name NAME]
                                  [--experiment_config EXPERIMENT_CONFIG]
                                  [-l KEY=VALUE] [--nonpreemptible]
                                  [--dry_run] [--export EXPORT]
                                  [--xgroup XGROUP]
                                  module ...

   submit cluster job(s)

   positional arguments:
     module                Code to execute, in either trainer.train' or
                           'trainer/train.py' format. Accepts python scripts,
                           modules or a path to an arbitrary script.

   optional arguments:
     -h, --help            show this help message and exit
     --helpfull            show full help message and exit
     --cluster_name CLUSTER_NAME
                           cluster name (default: None)
     --nogpu               Disable GPU mode and force CPU-only. (default: True)
     --cloud_key CLOUD_KEY
                           Path to GCloud service account key. (Defaults to
                           $GOOGLE_APPLICATION_CREDENTIALS.) (default: None)
     --extras EXTRAS       setup.py dependency keys. (default: None)
     -d DIR, --dir DIR     Extra directories to include. List these from large to
                           small to take full advantage of Docker's build cache.
                           (default: None)
     --image_tag IMAGE_TAG
                           Docker image tag accessible via Container Registry. If
                           supplied, Caliban will skip the build and push steps
                           and use this image tag. (default: None)
     --project_id PROJECT_ID
                           ID of the GCloud AI Platform/GKE project to use for
                           Cloud job submission and image persistence. (Defaults
                           to $PROJECT_ID; errors if both the argument and
                           $PROJECT_ID are empty.) (default: None)
     --min_cpu MIN_CPU     Minimum cpu needed by job, in milli-cpus. If not
                           specified, then this value defaults to 1500 for
                           gpu/tpu jobs, and 31000 for cpu jobs. Please note that
                           gke daemon processes utilize a small amount of cpu on
                           each node, so if you want to have your job run on a
                           specific machine type, say a 2-cpu machine, then if
                           you specify a minimum cpu of 2000, then your job will
                           not be schedulable on a 2-cpu machine as the daemon
                           processes will push the total cpu needed to more than
                           two full cpus. (default: None)
     --min_mem MIN_MEM     Minimum memory needed by job, in MB. Please note that
                           gke daemon processes utilize a small amount of memory
                           on each node, so if you want to have your job run on a
                           specific machine type, say a machine with 8GB total
                           memory, then if you specify a minimum memory of
                           8000MB, then your job will not be schedulable on a 8GB
                           machine as the daemon processes will push the total
                           memory needed to more than 8GB. (default: None)
     --gpu_spec NUMxGPU_TYPE
                           Type and number of GPUs to use for each AI
                           Platform/GKE submission. Defaults to 1xP100 in GPU
                           mode or None if --nogpu is passed. (default: None)
     --tpu_spec NUMxTPU_TYPE
                           Type and number of TPUs to request for each AI
                           Platform/GKE submission. Defaults to None. (default:
                           None)
     --tpu_driver TPU_DRIVER
                           tpu driver (default: 1.14)
     --nonpreemptible_tpu  use non-preemptible tpus: note this only applies to
                           v2-8 and v3-8 tpus currently, see:
                           https://cloud.google.com/tpu/docs/preemptible
                           (default: False)
     --force               Force past validations and submit the job as
                           specified. (default: False)
     --name NAME           Set a job name for AI Platform or GKE jobs. (default:
                           None)
     --experiment_config EXPERIMENT_CONFIG
                           Path to an experiment config, or 'stdin' to read from
                           stdin. (default: None)
     -l KEY=VALUE, --label KEY=VALUE
                           Extra label k=v pair to submit to Cloud. (default:
                           None)
     --nonpreemptible      use non-preemptible VM instance: please note that you
                           may need to upgrade your cluster to a recent
                           version/use the rapid release channel for preemptible
                           VMs to be supported with node autoprovisioning:
                           https://cloud.google.com/kubernetes-
                           engine/docs/release-notes-rapid#december_13_2019
                           (default: False)
     --dry_run             Don't actually submit; log everything that's going to
                           happen. (default: False)
     --export EXPORT       Export job spec(s) to file, extension must be one of
                           ('.yaml', '.json') (for example: --export my-job-
                           spec.yaml) For multiple jobs (i.e. in an experiment
                           config scenario), multiple files will be generated
                           with an index inserted (for example: --export my-job-
                           spec.yaml would yield my-job-spec_0.yaml, my-job-
                           spec_1.yaml...) (default: None)
     --xgroup XGROUP       This specifies an experiment group, which ties
                           experiments and job instances together. If you do not
                           specify a group, then a new one will be created. If
                           you specify an existing experiment group here, then
                           new experiments and jobs you create will be added to
                           the group you specify. (default: None)

   pass-through arguments:
     -- YOUR_ARGS          This is a catch-all for arguments you want to pass
                           through to your script. any arguments after '--' will
                           pass through.

Again, this command very closely mirrors :doc:`../cli/caliban_cloud`.

You can export job requests created with caliban as a ``yaml`` or ``json`` file
using the ``--export`` flag. You can then use this file with ``caliban cluster job
submit_file`` or
`\ ``kubectl`` <https://kubernetes.io/docs/concepts/workloads/controllers/jobs-run-to-completion/#running-an-example-job>`_
to submit the same job again.

``caliban cluster job submit_file``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This command submits a kubernetes k8s job file to your cluster. This can be
useful if you have a job that you run regularly, as you can create the job
initially with ``caliban cluster job submit`` and use the ``--export`` option to
save the job spec file. Then you can use this command to submit the job again
without having to specify all of the cli arguments.

The syntax of this command:

.. code-block:: text

   totoro@totoro:$ caliban cluster job submit_file --help
   usage: caliban cluster job submit_file [-h] [--helpfull]
                                          [--cluster_name CLUSTER_NAME]
                                          [--cloud_key CLOUD_KEY]
                                          [--project_id PROJECT_ID] [--dry_run]
                                          job_file

   submit gke job from yaml/json file

   positional arguments:
     job_file              kubernetes k8s job file ('.yaml', '.json')

   optional arguments:
     -h, --help            show this help message and exit
     --helpfull            show full help message and exit
     --cluster_name CLUSTER_NAME
                           cluster name (default: None)
     --cloud_key CLOUD_KEY
                           Path to GCloud service account key. (Defaults to
                           $GOOGLE_APPLICATION_CREDENTIALS.) (default: None)
     --project_id PROJECT_ID
                           ID of the GCloud AI Platform/GKE project to use for
                           Cloud job submission and image persistence. (Defaults
                           to $PROJECT_ID; errors if both the argument and
                           $PROJECT_ID are empty.) (default: None)
     --dry_run             Don't actually submit; log everything that's going to
                           happen. (default: False)

Thus a common invocation would resemble:

.. code-block:: text

   caliban cluster job submit_file my-job.yaml
