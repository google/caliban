Prerequisites
-------------

Before you can install and use Caliban to manage your research workflows, you'll
need a solid Cloud and Docker installation. Follow these steps to get set up.

Python 3
^^^^^^^^

If you're on a Mac, download
`Python 3.7.5 from python.org <https://www.python.org/downloads/mac-osx>`_
(\ `direct download link <https://www.python.org/ftp/python/3.7.5/python-3.7.5-macosx10.9.pkg>`_\ )

On a Linux machine, make sure your ``python3`` is up to date by running the
following command at your terminal:

.. code-block:: bash

   sudo apt-get install python3 python3-venv python3-pip

Once that's all set, verify that you're running python 3.7 or above:

.. code-block:: bash

   $ python3 --version
   Python 3.7.5 # Or something above 3.7.0

Docker and CUDA
^^^^^^^^^^^^^^^

Caliban uses Docker for each of its commands. To use Caliban, you'll need
``docker`` and (if you're on Linux) ``nvidia-docker`` on your machine.

If you're on a Mac, install `Docker Desktop for Mac <http://go/bs-mac-setup>`_
(so easy!) You'll only be able to run in CPU mode, as macs don't support
Docker's nvidia runtime. You will, however, be able to build GPU containers and
submit them to Google Cloud.

If you're on Linux, follow the instructions at the `nvidia-docker
<https://github.com/NVIDIA/nvidia-docker>`_ page to configure the ability to run
GPU containers locally.
