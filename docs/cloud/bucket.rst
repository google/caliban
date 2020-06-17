Creating a Bucket
^^^^^^^^^^^^^^^^^

If you need to store data that you generate during a :doc:`../cli/caliban_cloud`
run, storing data in a Cloud bucket is the easiest choice.

Your bucket is a reserved "folder" on the Cloud filesystem; you'll use this to
save models and measurements, and as a staging ground for model workflows you're
submitting to Cloud.

To create your bucket, add the following lines to your ``~/.bashrc`` file:

.. code-block:: bash

   export BUCKET_NAME="totoro_bucket"
   export REGION="us-central1"

Run ``source ~/.bashrc`` to pick up the changes, then run the following command
to create your new bucket:

.. code-block:: bash

   gsutil mb -l $REGION gs://$BUCKET_NAME

That's it.
