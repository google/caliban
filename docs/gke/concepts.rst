GKE Concepts
^^^^^^^^^^^^

Caliban makes it easy to create your own GKE Cluster - similar to your own
personal copy of AI Platform - in your Cloud project, and submit jobs to that
cluster. The advantage over AI Platform currently is that you can get more
quota, often 10x what you have available in AI Platform, and many features are
supported in GKE much earlier than they are in AI Platform.

The quota disparity is particularly notable with TPUs. AI Platform currently
only allows 8 TPUs, while a GKE cluster lets you specify 32, 64, etc TPUs for a
given job.

A good collection of GKE documentation can be found
`here <https://cloud.google.com/kubernetes-engine/docs/concepts>`_

Cluster
~~~~~~~

A
`cluster <https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-architecture>`_
is a collection of cloud machines, combining a set of *nodes* that run your
processing jobs, and *control plane* (also referred to as a *cluster master*\ )
that manages these worker nodes and handles scheduling your jobs and creating
worker nodes to run them.

Cluster Master
~~~~~~~~~~~~~~

A
`cluster master <https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-architecture#master>`_
is the controller for the cluster and all its resources. It handles creating and
deleting worker nodes, and scheduling jobs submitted by users.

Nodes
~~~~~

A
`node <https://cloud.google.com/kubernetes-engine/docs/concepts/cluster-architecture#nodes>`_
is a worker machine (a cloud compute engine instance) that actually performs the
work your job requires. The cluster control plane creates and manages these
instances.

Node Pool
~~~~~~~~~

A
`node pool <https://cloud.google.com/kubernetes-engine/docs/concepts/node-pools>`_
is a collection of identical nodes (cpu, memory, gpu, tpu).

Job
~~~

A
`job <https://cloud.google.com/kubernetes-engine/docs/concepts/batch-reference#batchjobs>`_
is a task that is to be run to completion using cluster resources. The cluster
control plane manages the resources the job needs and handles restarting the job
in case of failure or preemption. A job probably matches the concept you have in
mind when you think of a job you submit to AI platform. A job is a top-level
task, which may be run on multiple machines/containers, which in GKE are
referred to as *pods*\ , described below.

Pod
~~~

A `pod <https://cloud.google.com/kubernetes-engine/docs/concepts/pod>`_ is a
single, ephemeral, running execution of your container. A job may run on several
pods.
