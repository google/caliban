Job Labels
^^^^^^^^^^

AI Platform provides you with the ability to label your jobs with key-value
pairs. Any arguments you provide using either :doc:`custom script arguments
<../explore/custom_script_args>` or an :doc:`experiment broadcast
<../explore/experiment_broadcasting>` will be added to your job as labels, like
this:

In addition to arguments Caliban will add these labels to each job:


* **job_name**: ``caliban_totoro`` by default, or the argument you pass
  using ``caliban cloud --name custom_name``
* **gpu_enabled**\ : ``true`` by default, or ``false`` if you ran your job with
  ``--nogpu``

Cloud has fairly strict requirements on the format of each label's key and
value; Caliban will transform your arguments into labels with the proper
formatting, so you don't have to think about these.

Additional Custom Labels
~~~~~~~~~~~~~~~~~~~~~~~~

You can also pass extra custom labels using ``-l`` or ``--label``\ :

.. code-block:: bash

   caliban cloud -l key:value --label another_k:my_value ...

These labels will be applied to every job if you're running an :doc:`experiment
broadcast <../explore/experiment_broadcasting>`, or to the single job you're
submitting otherwise.

If you provide a label that conflicts with a user argument or experiment flag,
your label will get knocked out.

.. NOTE:: periods aren't allowed in labels, but are often quite meaningful;
   because of this caliban replaces periods with underscores before stripping
   out any restricted characters.
