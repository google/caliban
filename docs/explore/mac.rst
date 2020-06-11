Caliban on a Mac
^^^^^^^^^^^^^^^^^^^^^^

If you're developing on your Macbook, you'll be able to build GPU containers,
but you won't be able to run them locally. You can still submit GPU jobs to AI
Platform!

To use Caliban's ``shell``\ , ``notebook`` and ``run``\ , you'll have to pass
``--nogpu`` as a keyword argument. If you don't do this you'll see the following
error:

.. code-block:: text

   [totoro@totoro-macbookpro hello-tensorflow (master)]$ caliban run trainer.train

   'caliban run' doesn't support GPU usage on Macs! Please pass --nogpu to use this command.

   (GPU mode is fine for 'caliban cloud' from a Mac; just nothing that runs locally.)

The :doc:`../getting_started/prerequisites` page covers Macbook installation of
Docker and other dependencies.
