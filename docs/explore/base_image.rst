What's the Base Docker Image?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Caliban's modes build docker images using a dynamically generated ``Dockerfile``.
You'll see this ``Dockerfile`` stream to stdout when you run any of Caliban's
commands.

In addition to the isolation Docker provides, the images set up a Python virtual
environment inside of each container. This guarantees you a truly blank slate;
the dependencies you declare in your code directory are the only Python
libraries that will be present. No more version clashes or surprises.

Caliban uses one of two base images, depending on whether you're running in GPU
(default) or CPU mode:


* ``gcr.io/blueshift-playground/blueshift:gpu`` for the default GPU mode
* ``gcr.io/blueshift-playground/blueshift:cpu`` for CPU, or ``--nogpu``\ , mode

These are based on, respectively,


* ``tensorflow/tensorflow:2.0.0-gpu-py3``
* ``tensorflow/tensorflow:2.0.0-py3``

We chose the base Tensorflow containers only because they do the hard work of
installing all of the CUDA drivers and other software required by NVIDIA GPUs;
the virtual environment inside of the container isolates you from the installed
``tensorflow`` library. You can install any TF version you like, or use Jax or
Pytorch or any other system.

Here's a link to the
`Dockerfile <https://team.git.corp.google.com/blueshift/caliban/+/refs/heads/master/Dockerfile>`_
we use to build the two base images that sit behind all Docker images generated
by Caliban.