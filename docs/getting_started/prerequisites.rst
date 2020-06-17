Prerequisites
-------------

Before you can use Caliban you'll need to install Docker and make sure your
Python binary is up to date. Follow these steps to get set up.

Python 3
^^^^^^^^

Caliban requires Python >= 3.6. Check your current version at the terminal:

.. code-block:: bash

   $ python3 --version
   Python 3.6.9 # Or something above 3.6.0

If you need to upgrade:

on MacOS, download `the latest Python from python.org
<https://www.python.org/downloads/mac-osx>`_.

On a Linux machine, make sure your ``python3`` is up to date by running the
following command at your terminal:

.. code-block:: bash

   sudo apt-get install python3 python3-venv python3-pip

Once that's all set, run ``python3 --help`` again to verify that you're running python
3.6 or above.

Docker
^^^^^^

Caliban uses Docker for each of its commands. To use Caliban, you'll need
``docker`` and (if you're on Linux) ``nvidia-docker`` on your machine.

On MacOS, install `Docker Desktop for Mac
<https://hub.docker.com/editions/community/docker-ce-desktop-mac>`_. You'll only
be able to run in CPU mode, as MacOS doesn't support Docker's nvidia runtime.
You will, however, be able to build GPU containers and submit them to Google
Cloud.

On Linux, install Docker with `these instructions
<https://docs.docker.com/install/linux/docker-ce/ubuntu/>`_. add your username
to the docker group so that you can run Docker without using ``sudo``:

.. code-block:: bash

   sudo usermod -a -G docker ${USER}

Docker and CUDA
^^^^^^^^^^^^^^^

On Linux, Caliban can run jobs locally that take advantage of a GPU you may have installed.

To use this feature, install the ``nvidia-docker`` runtime by following the
instructions at the `nvidia-docker <https://github.com/NVIDIA/nvidia-docker>`_
page.
