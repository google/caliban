Cluster Management
^^^^^^^^^^^^^^^^^^

This section describes how to create and delete clusters. We'll add
documentation on other relevant cluster lifecycle tasks as we go.

Cluster Creation
~~~~~~~~~~~~~~~~

As described in the ``create`` section of :doc:`../cli/caliban_cluster`, you
will typically create a cluster once for a given project and leave it running.

You can create a cluster for your project as follows:

.. code-block:: bash

   totoro@totoro:$ caliban cluster create --cluster_name cluster_name --zone us-central1-a
   I0204 09:24:08.710866 139910209476416 cli.py:165] creating cluster cluster_name in project totoro-project in us-central1-a...
   I0204 09:24:08.711183 139910209476416 cli.py:166] please be patient, this may take several minutes
   I0204 09:24:08.711309 139910209476416 cli.py:167] visit https://console.cloud.google.com/kubernetes/clusters/details/us-central1-a/cluster_name?project=totoro-project to monitor cluster creation progress
   I0204 09:28:05.274621 139910209476416 cluster.py:1091] created cluster cluster_name successfully
   I0204 09:28:05.274888 139910209476416 cluster.py:1092] applying nvidia driver daemonset...

The command will typically take several minutes to complete. The command will
provide you with an url you can follow to monitor the creation process. The page
will look something like the following:

.. image:: /_static/img/gke/cluster_create_progress.png
  :width: 600
  :align: center
  :alt: Cluster creation progress

Once your cluster is created and running, you can view and inspect it from the
cloud dashboard from the ``Kuberenetes Engine > Clusters`` menu option:

.. image:: /_static/img/gke/cluster_dashboard.png
  :width: 600
  :align: center
  :alt: Cluster dashboard

Cluster Deletion
~~~~~~~~~~~~~~~~

In most cases you will bring up your cluster and leave it running. The cluster
master does consume resources, however, so if you know that you are not going to
be submitting jobs to your cluster for some length of time, you may want to
delete your cluster to save money. Before doing this, please make sure that all
of your jobs are complete, as deleting the cluster will also kill any running
jobs. Deleting the cluster is very straightforward, simply using the
:doc:`../cli/caliban_cluster` ``delete`` command.
