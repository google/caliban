What's the Base Docker Image?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Caliban's modes build docker images using a dynamically generated ``Dockerfile``.
You'll see this ``Dockerfile`` stream to stdout when you run any of Caliban's
commands. You can specify the base image you wish to use in your ``.calibanconfig.json``
file as described :ref:`here<calibanconfig>`.

In addition to the isolation Docker provides, the images set up a Python virtual
environment inside of each container. This guarantees you a truly blank slate;
the dependencies you declare in your code directory are the only Python
libraries that will be present. No more version clashes or surprises.

Caliban uses a set of base images covering a set of common combinations of
python and cuda versions. You can find our base images
`here <https://gcr.io/blueshift-playground/blueshift>`_.
The format of our base image names is ``gcr.io/blueshift-playground/blueshift:TAG``,
where ``TAG`` describes the configuration of the base image.

For example, ``gcr.io/blueshift-playground/blueshift:gpu-ubuntu1804-py38-cuda101`` is a
gpu base image that uses Ubuntu 18.04, CUDA 10.1 and python 3.8, while
``gcr.io/blueshift-playground/blueshift:cpu-ubuntu2004-py38`` is a cpu-only Ubuntu 20.04
base image that has no CUDA support and uses python 3.8.

Our current supported combinations:

+--------------+------------+------------+
| Ubuntu 18.04 | python 3.7 | python 3.8 |
+--------------+------------+------------+
|   no cuda    |    yes     |    yes     |
+--------------+------------+------------+
|   cuda 10.0  |    yes     |    yes     |
+--------------+------------+------------+
|   cuda 10.1  |    yes     |    yes     |
+--------------+------------+------------+


+--------------+------------+------------+
| Ubuntu 20.04 | python 3.7 | python 3.8 |
+--------------+------------+------------+
|   no cuda    |    yes     |    yes     |
+--------------+------------+------------+
|   cuda 10.0  |    no      |     no     |
+--------------+------------+------------+
|   cuda 10.1  |    no      |     no     |
+--------------+------------+------------+


These images are automatically updated, and if you have an image combination that
we don't support, please file an issue and we'll consider adding it to our set
of supported images. We are planning to add support for custom base images so
you can build and use your own specialized image.

The dockerfiles we use to generate our supported images can be found
`here <https://github.com/google/caliban/tree/master/dockerfiles>`_. We create
base gpu images from the `Dockerfile.gpu <https://github.com/google/caliban/blob/master/dockerfiles/Dockerfile.gpu>`_
file, and then use these as base images for creating full GPU images with
support for specific python versions using this `Dockerfile <https://github.com/google/caliban/blob/master/dockerfiles/Dockerfile>`_.

We base our gpu base images on the `nvidia/cuda <https://hub.docker.com/r/nvidia/cuda/>`_
images, which contain the relevant CUDA drivers required for GPU use. The virtual
environment inside of the Caliban container isolates you from these low-level details,
so you can install any tensorflow version you like, or use Jax or Pytorch or any
other system.

Details for Maintainers
~~~~~~~~~~~~~~~~~~~~~~~

We utilize Google's `Cloud Build <http://cloud.google.com/cloud-build/docs>`_ service
to build Caliban's base images. Our Cloud Build configuration file that controls
our image generation can be found in the source repository
`here <https://github.com/google/caliban/blob/master/cloudbuild.json>`_.

This file can quickly get lengthy and difficult to maintain, so we generate this file
using `a script <https://github.com/google/caliban/blob/master/scripts/cloudbuild.py>`_
and `a configuration file <https://github.com/google/caliban/blob/master/scripts/cloudbuild_config.json>`_.
In the configuration file, we specify our supported CUDA versions, our supported
python versions, and a list of the combinations we use in our supported images.
For our CUDA and python versions, we specify a list of build-args that we then
pass to the docker build process for the Dockerfiles described above.

To generate a new ``cloudbuild.json`` file, invoke the ``cloudbuild.py`` utility with
your configuration file:

.. code-block:: bash

   python ./scripts/cloudbuild.py --config scripts/cloudbuild_config.json  --output cloudbuild.json

This will generate a new ``cloudbuild.json`` file which is used by the Cloud Build service
to generate our base docker images. For testing, you can set a different base image url for
the docker images by using the ``--base_url`` keyword argument.

To manually start a Cloud Build for these docker images, navigate to the top-level
of the caliban source repository, and use the
`gcloud builds <https://cloud.google.com/cloud-build/docs/running-builds/start-build-manually#gcloud>`_
command:

.. code-block:: bash

   gcloud builds submit --project=<destination project> --config=cloudbuild.json .

By default this uses your default project and the ``cloudbuild.json`` file in your current
directory. If you are pushing the images to a different project than your ``gcloud`` default,
then you may need to set the ``--project`` flag to the target project where you are pushing
your images. The logs from the build process will be streamed to your console, but they are
also available from the ``Cloud Build`` tab in the GCP dashboard for your project.

To automate the generation of these images, we utilize
`build triggers <https://cloud.google.com/cloud-build/docs/automating-builds/create-manage-triggers>`_
to start a new cloud build whenever the Caliban Dockerfiles are modified in the repository.
