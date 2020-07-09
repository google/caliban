Setting up Google Cloud
=======================

This document will guide you through the process of configuring your machine to
submit jobs to Google's Cloud AI Platform with :doc:`../cli/caliban_cloud`.

.. note:: Caliban will eventually support other Cloud providers like AWS, but
   Google Cloud will remain a great starting option. Google Cloud gives you $300
   of credit, so you can get started immediately with
   :doc:`../cli/caliban_cloud`.

By the end you'll be able to complete the `final step
<https://github.com/google/caliban#submitting-to-cloud-ai-platform>`_ of the
`"Getting Started with Caliban"
<https://github.com/google/caliban#getting-started-with-caliban>`_ tutorial and
train an ML model on AI Platform.

**These are the steps we'll cover**:

.. contents:: :local:
   :depth: 1

To make it through, you'll **need to know**:

- Know how to `save environment variables on your machine
  <https://scotch.io/tutorials/how-to-use-environment-variables>`_ by saving
  them in your ``~/.bashrc`` file.

Create a Cloud Account
----------------------

To submit jobs to AI Platform you need to create a Google Cloud account with an
active "`project
<https://cloud.google.com/resource-manager/docs/creating-managing-projects>`_".
Every job you submit to Cloud will be associated with this project.

Visit the `Google Cloud Console <https://console.cloud.google.com>`_ and click
"Select a Project":

.. image:: /_static/img/cloud/select_project.png
  :width: 600
  :align: center
  :alt: Select a Project

Click "New Project" in the dialogue that appears:

.. image:: /_static/img/cloud/new_project.png
  :width: 600
  :align: center
  :alt: New Project

Give your project a memorable name like "totoro-lives" and click Create. This
should take you to your new project's dashboard.

Note the **Project ID** in the "Project info" panel:

.. image:: /_static/img/cloud/project_id.png
  :width: 600
  :align: center
  :alt: Project ID

Caliban will use this project ID to submit jobs to the correct project in Cloud.

Add the following line to the file ``~/.bashrc`` or ``~/.bash_profile`` on your
machine, to make the ID available to Caliban:

.. code-block:: bash

   export PROJECT_ID=<your-project-id>

.. note:: If you don't know what this means, see `this page
          <https://scotch.io/tutorials/how-to-use-environment-variables>`_ for a
          tutorial on environment variables. We'll remind you at the end of the
          tutorial which variables you'll need.


Activate Free Cloud Trial
-------------------------

Every new Google Cloud project comes with a free $300 credit. To activate this,
click "Activate" at the top right of your new Cloud account's console and follow
the prompts.

.. image:: /_static/img/cloud/activate.png
  :width: 600
  :align: center
  :alt: Activate Billing

You'll have to set up a billing account as well.

The system will ask you for a credit card to verify your identity, but if you
use up the entire credit it won't automatically charge you. You can decide at
that point whether you'd like to continue or not.

Enable AI Platform and Container Registry
-----------------------------------------

Google Cloud has a `dizzying number of products
<https://cloud.google.com/products>`_. To submit jobs with
:doc:`/cli/caliban_cloud`, you'll need to activate just these two:

- `Cloud AI Platform <https://cloud.google.com/ai-platform/docs>`_
- `Container Registry <https://cloud.google.com/container-registry/docs/quickstart>`_

Follow the instructions at `this link to enable the Container Registry API
<https://console.cloud.google.com/flows/enableapi?apiid=containerregistry.googleapis.com&redirect=https://cloud.google.com/container-registry/docs/quickstart&_ga=2.204958805.498449691.1592416944-1401171737.1587152715>`_
by selecting the project you created above and clicking "Continue".

Click `this link to Enable the AI Platform Jobs API
<https://console.cloud.google.com/ai-platform/ml-enable-api/jobs>`_ by clicking
"Enable API" and waiting for the spinner to stop.

Install the Cloud SDK
---------------------

The final step is to install the `Google Cloud SDK
<https://cloud.google.com/sdk/install>`_ on your machine.

Visit the `Google Cloud SDK installation page
<https://cloud.google.com/sdk/install>`_ for a full set of installation
instructions. Here is the distilled version:

- For MacOS, run the `interactive installer
  <https://cloud.google.com/sdk/docs/downloads-interactive>`_.
- For Linux, use `apt-get
  <https://cloud.google.com/sdk/docs/downloads-apt-get>`_ to get the latest
  release.

If you didn't do it during installation, you'll need to initialize the SDK with this command:

.. code-block:: bash

   gcloud init

When you see this output:

.. code-block:: bash

   You are logged in as: [totoro@gmail.com].

   This account has a lot of projects! Listing them all can take a while.
    [1] Enter a project ID
    [2] Create a new project
    [3] List projects
   Please enter your numeric choice:

Enter ``1``, then type in your project ID you noted earlier. (You should have
saved it as an environment variable called ``$PROJECT_ID``).

If you'd like to set a default zone, anything beginning with ``us-central1`` is
a great choice. ``us-central1`` has `the most capability
<https://cloud.google.com/ml-engine/docs/regions>`_ of any region.

.. note:: the Cloud SDK is quite powerful, and gives you access to Cloud buckets
          and all sorts of Google services. You might want to peruse the full
          set of `SDK documentation
          <https://cloud.google.com/sdk/gcloud/reference/>`_ once you've got
          everything working.

Configure Docker Authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To submit a job with :doc:`/cli/caliban_cloud`, Caliban needs to push Docker
images to the Container Registry service that you enabled earlier. To allow
Docker to push to the Container Registry, run this command at a terminal:

.. code-block:: bash

   gcloud auth configure-docker

You should see output that includes the text ``Adding credentials for all GCR
repositories.``.

Test your Environment
---------------------

To check if your SDK installation was successful, run ``gcloud auth list`` in
your terminal. You should see your email address listed as the active account:

.. code-block:: bash

   [totoro@totoro ~]$ gcloud auth list
       Credentialed Accounts
   ACTIVE  ACCOUNT
   *       totoro@google.com

   To set the active account, run:
       $ gcloud config set account `ACCOUNT`

As a final step, confirm that you've set the following environment variables.
(If you set a custom region above, add it here as a ``$REGION`` variable).

.. code-block:: bash

   export REGION="us-central1"
   export PROJECT_ID="research-3141"

If you have all of this, you're set!

Train a model in Cloud
----------------------

Now that you have a working Cloud configuration and a new project, you can use
:doc:`/cli/caliban_cloud` to submit jobs to Cloud AI platform.

The `"Getting Started with Caliban"
<https://github.com/google/caliban#getting-started-with-caliban>`_ tutorial ends
with a nice demo that has you training models in Cloud. Head over to `the
tutorial <https://github.com/google/caliban#getting-started-with-caliban>`_ and
complete the `final step
<https://github.com/google/caliban#submitting-to-cloud-ai-platform>`_ to train a
digit-classifying neural network on AI Platform.
