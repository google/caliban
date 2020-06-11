Prerequisites
-------------

Before you can install and use Caliban to manage your research workflows, you'll
need a solid Cloud and Docker installation. Follow these steps to get set up.

Python 3
^^^^^^^^

Make sure your ``python3`` is up to date by running the following command at your
workstation:

.. code-block:: bash

   sudo apt-get install python3 python3-venv python3-pip

If you're on a Mac, download
`Python 3.7.5 from python.org <https://www.python.org/downloads/mac-osx>`_
(\ `direct download link <https://www.python.org/ftp/python/3.7.5/python-3.7.5-macosx10.9.pkg>`_\ )

Once that's all set, verify that you're running python 3.5 or above:

.. code-block:: bash

   $ python3 --version
   Python 3.7.5 # Or something above 3.5.3

Blueshift Internal Repo
^^^^^^^^^^^^^^^^^^^^^^^

The `Blueshift internal repository <http://go/bs-internal>`_ has some nice tooling
that will make life easier at Blueshift.

To get the Blueshift repository installed, run these three commands:

.. code-block:: bash

   git clone sso://team/blueshift/blueshift ~/dev/blueshift
   echo -e '\n#Blueshift shared aliases and functions\nsource ~/dev/blueshift/profile/bashrc' >> ~/.bashrc
   source ~/.bashrc

Please modify the above if you're using a different shell like ``zsh``.

Docker and CUDA
^^^^^^^^^^^^^^^

Caliban uses Docker for all of its tasks. To use Caliban, you'll need ``docker``
and\ ``nvidia-docker`` on your machine. Use Blueshift's
`Working with Docker <http://go/bs-docker>`_ tutorial at go/bs-docker to get
yourself set up.

If you're on a Mac laptop, just install
`Docker Desktop for Mac <http://go/bs-mac-setup>`_ (so easy!)

If you're on a workstation, you'll also need to make sure that your CUDA drivers
are up to date, and that you have a big-iron GPU installed in your workstation.

If you've installed the `Blueshift repository <http://go/bs-internal>`_ this
part's easy. Just open a new terminal window. If you don't see any warnings
about CUDA, you're set!

If you still need to install a physical GPU in your workstation, the
`Workstation GPU installation <http://go/bs-gpus>`_ tutorial at go/bs-gpus will
get you sorted.
