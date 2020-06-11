Experiment Broadcasting
^^^^^^^^^^^^^^^^^^^^^^^

The ``--experiment_config`` keyword argument allows you to pass Caliban a config
that can run many instances of your containerized job by passing each job a
different combination of some set of parameters. These parameters are passed to
your job as ``--key value`` style flags that you can parse with
`\ ``abseil`` <https://abseil.io/docs/python/quickstart>`_ or
`\ ``argparse`` <https://docs.python.org/3/library/argparse.html>`_.

This keyword is accepted by the following subcommands:


* ``caliban cloud``\ , to submit experiments to AI Platform
* ``caliban run`` to run experiments in sequence on a local workstation
* ``caliban cluster`` to execute experiments on a GKE cluster

The documentation below will refer to ``caliban cloud``\ , but all commands will
work just as well with these other modes unless explicitly called out otherwise.

``--experiment_config`` accepts a path, local or absolute, to a JSON file on your
local machine. That JSON file defines a sweep of parameters that you'd like to
explore in an experiment. Let's look at the format, and what it means for job
submission.

Experiment.json Format
~~~~~~~~~~~~~~~~~~~~~~

You can name the file whatever you like, but we'll refer to it here as
``experiment.json`` always. Here's an example ``experiment.json`` file:

.. code-block:: json

   {
       # comments work inside the JSON file!
       "epochs": [2, 3],
       "batch_size": [64, 128], # end of line comments too.
       "constant_arg": "something"
       "important_toggle": [true, false]
   }

The following command will submit an experiment using the above experiment
definition:

.. code-block:: bash

   caliban cloud --experiment_config ~/path/to/experiment.json trainer.train

For this particular ``experiment.json`` file, Caliban will submit 8 different jobs
to AI Platform with the following combinations of flags, one combination for
each job:

.. code-block:: bash

   --epochs 2 --batch_size 64 --constant_arg 'something' --important_toggle
   --epochs 2 --batch_size 64 --constant_arg 'something'
   --epochs 2 --batch_size 128 --constant_arg 'something' --important_toggle
   --epochs 2 --batch_size 128 --constant_arg 'something'
   --epochs 3 --batch_size 64 --constant_arg 'something' --important_toggle
   --epochs 3 --batch_size 64 --constant_arg 'something'
   --epochs 3 --batch_size 128 --constant_arg 'something' --important_toggle
   --epochs 3 --batch_size 128 --constant_arg 'something'

As you can see, keys get expanded out into ``--key`` style flags by prepending a
``--`` onto the key string. Here are the rules for value expansion:


* ``int`` and ``string`` values are passed on to every job untouched.
* lists generate multiple jobs. ``caliban cloud`` takes the cartesian product of
  all list-type values and generates a job for each combination. Three lists
  of length 2 in the above example gives us 8 total jobs; one for each
  possible combination of items from each list.
* if a value equals ``true``\ , the key is passed through as ``--key``\ , with no
  value; it's treated as a boolean flag.
* a ``false`` boolean value means that the ``--key`` flag is ignored.

All arguments generated from the experiment config will create labels in the AI
Platform Job UI for each job as described in the :doc:`../cloud/labels` section.

Any :doc:`custom script arguments <custom_script_args>` you pass after the
module name, separated by ``--``\ , will be passed along to every job as if they
were static key-value pairs in the ``experiment.json`` file. As an example, the
following command:

.. code-block:: bash

   caliban cloud --experiment_config ~/path/to/experiment.json trainer.train -- --key value

would trigger the same jobs as before, with ``--key value`` appended BEFORE the
arguments broadcast out by the experiment config:

.. code-block:: bash

   --key value --epochs 2 --batch_size 64 --constant_arg 'something' --important_toggle
   --key value --epochs 2 --batch_size 64 --constant_arg 'something'
   # ....etc

Lists of Experiment Definitions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can pass either an experiment config or a LIST of experiment configs in your
``experiment.json`` file; caliban will expand each entry in the list recursively.
This makes it possible to generate experiment configs that aren't strict
cartesian products.

For example you might add the following to a file called ``experiment.json``\ , and
pass it to your job with ``--experiment_config experiment.json``\ :

.. code-block:: json

   [
       {
           "epochs": [1,2, 3, 4],
           "batch_size": [64, 128],
           "constant_arg": "something",
           "important_toggle": [true, false]
       },
       {
           "epochs": [9, 10],
           "batch_size": [512, 1024],
           "constant_arg": "something"
       }
       {
           "epochs": 1000,
           "batch_size": 1
       }
   ]

This config will generate:


* 16 combinations for the first dictionary (every combination of 4 epoch
  entries, 2 batch sizes, and 2 ``"important_toggle"`` combos, with
  ``"constant_arg"`` appended to each)
* 4 combos for the second dictionary
* 1 static combo for the third entry.

for a total of 21 jobs. You can always pass ``--dry_run`` (see below) to ``caliban
cloud`` to see what jobs will be generated for some experiment config, or to
validate that it's well-formed at all.

Compound keys
~~~~~~~~~~~~~

By default, an experiment specification in which multiple values are lists will
be expanded using a Cartesian product, as described above. If you want multiple
arguments to vary in concert, you can use a compound key. For example, the
following (w/o compound keys) experiment config file will result in four jobs
total:

.. code-block:: json

   {
     "a": ["a1", "a2"],
     "b": ["b1", "b2"]
   }

Results in:

.. code-block:: bash

   --a a1 --b b1
   --a a1 --b b2
   --a a2 --b b1
   --a a2 --b b2

To tie the values of ``a`` and ``b`` together, specify them in a compound key:

.. code-block:: json

   {
     "[a,b]": [["a1", "b1"], ["a2", "b2"]]
   }

This will result in only two jobs: ``bash --a a1 --b b1 --a a2 --b b2``

``--dry_run``
~~~~~~~~~~~~~~~~~

Passing an ``--experiment_config`` to ``caliban cloud`` could potentially submit
many, many jobs. To verify that you have no errors and are submitting the number
of jobs you expect, you can add the ``--dry_run`` flag to your command, like this:

.. code-block:: bash

   caliban cloud --dry_run --experiment_config ~/path/to/experiment.json trainer.train

``--dry_run`` will trigger all of the logging side effects you'd see on job
submission, so you can verify that all of your settings are correct. This
command will skip any docker build and push phases, so it will return
immediately with no side effects other than logging.

Once you're sure that your jobs look good and you pass all validations, you can
remove ``--dry_run`` to submit all jobs.

Experiments and Custom Machine + GPUs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you supply a ``--gpu_spec`` or ``--machine_type`` in addition to
``--experiment_config``\ , every job in the experiment submission will be configured
with those options.
