Prerequisites
-------------

Before you can use Caliban, you'll need to install Docker and make sure your
Python 3 is up to date. Follow these steps to get set up.

Python 3
^^^^^^^^

Caliban requires Python >= 3.6. Check your current version at the terminal:

.. code-block:: bash

   $ python3 --version
   Python 3.6.9 # Or something above 3.6.0

If you need to upgrade:

- on MacOS, download `the latest Python from python.org
  <https://www.python.org/downloads/mac-osx>`_.
- On Linux, make sure your ``python3`` is up to date by running the following
  command at your terminal:

.. code-block:: bash

   sudo apt-get install python3 python3-venv python3-pip

Once that's all set, run ``python3 --help`` again to verify that you're running
python 3.6 or above.

Docker
^^^^^^

To use Caliban, you'll need a working Docker installation. If you have a GPU and
want to run jobs that use it, you'll have to install ``nvidia-docker2``, as
described below in :ref:`GPU Support on Linux Machines`

- On MacOS, install `Docker Desktop for Mac
  <https://hub.docker.com/editions/community/docker-ce-desktop-mac>`_. You'll
  only be able to run in CPU mode, as MacOS doesn't support Docker's nvidia
  runtime. You will, however, be able to build GPU containers and submit them to
  Google Cloud.
- On Linux, install Docker with `these instructions
  <https://docs.docker.com/install/linux/docker-ce/ubuntu/>`_.

Add your username to the docker group so that you can run Docker without using
``sudo``:

.. code-block:: bash

   sudo usermod -a -G docker ${USER}

GPU Support on Linux Machines
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On Linux, Caliban can run jobs locally that take advantage of a GPU you may have installed.

To use this feature, install the ``nvidia-docker2`` runtime by following the
instructions at the `nvidia-docker2
<https://github.com/NVIDIA/nvidia-docker/wiki/Installation-(version-2.0)>`_
page.

.. NOTE:: It's important that you install ``nvidia-docker2``, not
          ``nvidia-docker``! The `nvidia-docker2
          <https://github.com/NVIDIA/nvidia-docker/wiki/Installation-(version-2.0)>`_
          instructions discuss how to upgrade if you accidentally install
          ``nvidia-docker``.

.. NOTE:: The most recent versions of docker don't need the ``nvidia-docker2``
          dependency. In a future version of Caliban we'll remove this
          dependency and upgrade the documentation.
