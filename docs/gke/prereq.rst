GKE Prerequisites
^^^^^^^^^^^^^^^^^

There are a few prerequisites for creating and submitting jobs to a gke cluster.

Required Permissions
~~~~~~~~~~~~~~~~~~~~

To create and use a GKE cluster, you'll need to modify your service account key
to give it Account Owner permissions. Those instructions live at the
:doc:`/cloud/service_account` docs page. Note that this only applies if you are
using a service account key.
