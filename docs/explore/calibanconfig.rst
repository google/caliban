calibanconfig
^^^^^^^^^^^^^^^^^^^^^^

Caliban supports customization through a file called ``.calibanconfig.json``
that lives in your project's directory. Features are limited for now, but stay
tuned for more.

Custom Apt Packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Caliban provides support for custom aptitude packages inside your container. To
require custom apt packages, create a file called ``.calibanconfig.json`` inside
your project's directory.

The ``.calibanconfig.json`` should contain a single JSON dictionary with an
``"apt_packages"`` key. The value under this key can be either a list, or a
dictionary with ``"gpu"`` and ``"cpu"'`` keys. For example, any of the following are
valid:

.. code-block::

   # This is a list by itself. Comments are fine, by the way.
   {
        "apt_packages": ["libsm6", "libxext6", "libxrender-dev"]
   }

This works too:

.. code-block:: json

   # You can also include a dictionary with different deps
   # for gpu and cpu modes. It's fine to leave either of these blank,
   # or not include it.
   {
       "apt_packages": {
           "gpu": ["libsm6", "libxext6", "libxrender-dev"],
           "cpu": ["some_other_package"]
       }
   }

These values will do what you expect and run ``apt-get install <package_name>``
for each package. Packages are alphabetized, so changing the order won't
invalidate Docker's build cache.

Custom Base Images
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
For details on Caliban's base images, see :ref:`What's the Base Docker Image?`.

You can specify a custom base image for Caliban to use in your ``.calibanconfig.json`` file
by adding an entry with the ``base_image`` key as follows:

.. code-block:: json

   {
       "base_image": "gcr.io/blueshift-playground/blueshift:gpu-ubuntu1804-py38-cuda101"
   }

You can also specify different base images for ``cpu`` and ``gpu`` modes as follows:

.. code-block:: json

   {
       "base_image": {
           "cpu": "gcr.io/blueshift-playground/blueshift:cpu-ubuntu1804-py38",
           "gpu": "gcr.io/blueshift-playground/blueshift:gpu-ubuntu1804-py38-cuda101"
       }
   }
