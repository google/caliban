TPUs on AI Platform
^^^^^^^^^^^^^^^^^^^

.. NOTE:: This documentation is currently quite sparse; expect a tutorial soon.

.. IMPORTANT:: Unlike on Cloud, TPUs on AI Platform only support (as of
   Dec 2019) Tensorflow versions 1.13 and 1.14. No Jax, no Pytorch.

Caliban has Tensorflow version 2.1 hardcoded internally. Once the range of
possible values expands we'll make this customizable.

See `AI Platform's runtime version list
<https://cloud.google.com/ml-engine/docs/runtime-version-list>`_ for more
detail.


If you supply the ``--tpu_spec NUM_TPUSxTPU_TYPE`` argument to your ``caliban
cloud`` job, AI Platform will configure a worker node with that number of TPUs
and attach it to the master node where your code runs.

``--tpu_spec`` is compatible with ``--gpu_spec``\ ; the latter configures the master
node where your code lives, while the former sets up a separate worker instance.

CPU mode by Default
~~~~~~~~~~~~~~~~~~~

Normally, all jobs default to GPU mode unless you supply ``--nogpu`` explicitly.
This default flips when you supply a ``--tpu_spec`` and no explicit ``--gpu_spec``.
In that case, ``caliban cloud`` will NOT attach a default GPU to your master
instance. You have to ask for it explicitly.

A CPU mode default also means that by default Caliban will try to install the
``'cpu'`` extra dependency set in your ``setup.py``\ , as described in the
:doc:`../explore/declaring_requirements` guide.

Authorizing TPU Access
~~~~~~~~~~~~~~~~~~~~~~

Before you can pass ``--tpu_spec`` to a job you'll need to authorize your Cloud
TPU to access your service account. Check out `the AI Platform TPU tutorial
<https://cloud.google.com/ml-engine/docs/tensorflow/using-tpus#authorize-tpu>`_
for detailed steps on how to achieve this.

Example Workflows
~~~~~~~~~~~~~~~~~

Next you'll need to get the repository of TPU examples on your machine.

.. code-block:: bash

   mkdir tpu-demos && cd tpu-demos
   curl https://codeload.github.com/tensorflow/tpu/tar.gz/r1.14 -o r1.14.tar.gz
   tar -xzvf r1.14.tar.gz && rm r1.14.tar.gz

Check out the
`AI Platform TPU tutorial <https://cloud.google.com/ml-engine/docs/tensorflow/using-tpus#authorize-tpu>`_
for the next steps, and check back for more detail about how to use that
tutorial with Caliban.
