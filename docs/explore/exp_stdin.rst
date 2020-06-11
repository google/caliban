Experiment Config via stdin, pipes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In addition to passing an explicit JSON file to ``caliban cloud
--experiment_config``\ , if you pass the string ``stdin`` as the flag's value
``caliban cloud`` will attempt to read the experiment config in off of ``stdin``.

As an example, this command pipes in a config and also passes ``--dry_run`` to
show the series of jobs that WILL be submitted when the ``--dry_run`` flag is
removed:

.. code-block:: bash

   cat experiment.json | caliban cloud --experiment_config stdin --dry_run trainer.train

Because ``experiment.json`` is a file on disk, the above command is not that
interesting, and equivalent to running:

.. code-block:: bash

   caliban cloud --experiment_config experiment.json --dry_run trainer.train

Things get more interesting when you need to dynamically generate an experiment
config.

Imagine you've written some python script ``generate_config.py`` that builds up a
list of complex, interdependent experiments. If you modify that script to print
a ``json`` list of ``json`` dicts when executed, you can pipe the results of the
script directly into ``caliban cloud``\ :

.. code-block:: bash

   python generate_config.py --turing_award 'winning' | \
     caliban cloud --experiment_config stdin --dry_run trainer.train

And see immediately (thanks to ``--dry_run``\ ) the list of jobs that would be
executed on AI Platform with a real run.


Experiment File Expansion and Pipes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :doc:`../cli/expansion` command described :doc:`above <../cli/expansion>`
allows you to expand an experiment config into its component JSON objects.
Because these are printed to ``stdout``\ , you can pipe them directly in to
Caliban's commands, like this:

.. code-block:: bash

   expansion experiment.json | caliban cloud --experiment_config stdin trainer.train

You can also insert your own script into the middle of this pipeline. Imagine a
script called ``my_script.py`` that:


* reads a JSON list of experiments in via ``stdin``
* modifies each entry by inserting a new key whose value is a function of one
  or more existing entries
* prints the resulting JSON list back out to ``stdout``

You could sequence these steps together like so:

.. code-block:: bash

   cat experiment.json | \
     expansion experiment.json | \
     my_script.py | \
     caliban cloud --experiment_config stdin --dry_run trainer.train

If you supply ``--dry_run`` to caliban, as in the example above, caliban will
print out all of the jobs that this particular command will kick off when you
remove ``--dry_run``. This is a great way to generate complex experiments and test
everything out before submitting your jobs.
