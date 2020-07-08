GCloud and GSUtil Authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Caliban supports authentication with GCloud and GSUtil via two methods:


* `Service Account Keys <https://cloud.google.com/iam/docs/creating-managing-service-account-keys>`_\ ,
  and
* `Application Default Credentials <https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login>`_

Service accounts keys (described in :doc:`../getting_started/cloud`) are the
method of authentication you'll find recommended by most Cloud documentation for
authentication within Docker containers.

 You might also come across a different method of authentication called
"Application Default Credentials", or ADC Credentials. See :doc:`../cloud/adc`
for more information.

.. NOTE:: to set up service account keys, visit the :doc:`service
   account instructions </cloud/service_account>`. To generate application default
   credentials on your machine, simply run ``gcloud auth application-default
   login`` at your terminal, as described `in the Google Cloud docs
   <https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login>`_.

If you've logged in to ``gcloud`` on your machine using application default
credentials, Caliban will copy your stored ADC credentials into your container.
If you DON'T have a service account, gcloud and the cloud python SDK will use
these ADC credentials inside the container and work just as they do on your
workstation.

If you've followed the service account key instructions above and declared a
``GOOGLE_APPLICATION_CREDENTIALS`` environment variable on your system pointing to
a Cloud JSON service account key, Caliban will copy that key into the container
that it builds and set up an environment variable in the container pointing to
the key copy.

You can set or override this variable for a specific caliban command by
supplying ``--cloud_key ~/path/to/my_key.json``\ , like so:

.. code-block:: bash

   caliban run --cloud_key ~/path/to/my_key.json trainer.train

.. WARNING:: If you supply this option to ``caliban shell`` or ``caliban
   notebook`` and have ``GOOGLE_APPLICATION_CREDENTIALS`` set in your
   ``.bashrc``, that variable will overwrite the key that the ``--cloud_key``
   option pushes into your container. To get around this, pass ``--bare`` to
   ``caliban shell`` or ``caliban notebook`` to prevent your home directory from
   mounting and, by extension, any of your environment variables from
   overwriting the environment variable set inside the container.

The environment variable and/or option aren't necessary, but if you don't have
either of them AND you don't have ADC credentials on your machine, you won't be
able to use the GCloud Python API or the ``gsutil`` or ``gcloud`` commands inside
the container.

As noted above, if you don't have this variable set up yet and want to get it
working, check out the :doc:`service account instructions
</cloud/service_account>`. To generate application default credentials on your
machine, simply run ``gcloud auth application-default login`` at your terminal,
as described `in the Cloud docs
<https://cloud.google.com/sdk/gcloud/reference/auth/application-default/login>`_.

GCloud SDK
~~~~~~~~~~

The `GCloud SDK <https://cloud.google.com/sdk/>`_ (\ ``gsutil``\ , ``gcloud`` and friends)
is also available inside of the containerized environment.

On your local machine, ``gsutil`` and ``gcloud`` are authorized using your Google
credentials and have full administrative access to anything in your project.
Inside of the container, these tools are authenticated using the JSON service
account key; this means that if your service account key is missing permissions,
you may see a mismatch in behavior inside the container vs on your workstation.

Shell Mode Caveats
~~~~~~~~~~~~~~~~~~

``caliban shell`` introduces one potentially confusing behavior with these Cloud
credentials. By default, ``caliban shell`` will mount your home directory inside
the container; it does this so that you have all of your bash aliases and your
familiar environment inside of the container. (You can disable this with the
``--bare`` option by running ``caliban shell --bare``\ ).

Mounting your ``$HOME`` directory will trigger an evaluation of your
``$HOME/.bashrc`` file, which will ``export GOOGLE_APPLICATION_CREDENTIALS`` and
overwrite the service key variable that Caliban has set up inside of the
container.

If you use a relative path for this variable on your workstation, like:

.. code-block:: bash

   export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/devkey.json"

then everything will still work out wonderfully; inside of the container,
``$HOME`` will resolve to the in-container ``$HOME``\ , but because everything on your
workstation's ``$HOME`` is mounted the container environment will find the key.

If, instead, you use an absolute path, like:

.. code-block:: bash

   export GOOGLE_APPLICATION_CREDENTIALS="/usr/local/google/home/totoro/.config/devkey.json"

The key won't resolve inside the container. (This only applies in ``caliban
shell`` and ``caliban notebook``\ , not in ``caliban {cloud,run}``.)

To fix this, just change your absolute path to a relative path and everything
will work as expected:

.. code-block:: bash

   export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/devkey.json"
