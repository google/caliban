# Cloud Tutorial

This repository contains a workflow that trains a vanilla fully-connected neural
network to predict MNIST digits, using Tensorflow's SGD optimizer.

The training code is compatible with Tensorflow 2.0, but the `setup.py` file
requires TF `1.14.*`; this is because AI Platform (as of 10.31.2019) doesn't yet
support TF2.

## Local Execution

First we'll all install the project's dependencies and execute a run using your
system's python installation. Before running the project, create a new
`virtualenv`.

Once you've activated your `virtualenv`, run the following command from the
`cloud_tutorial` project directory:

```bash
pip install .[local] # Install all dependencies locally

JOB_DIR="output-dist"
python trainer/train.py --job-dir $JOB_DIR
```

If you pass in `--help`, you'll see a number of options that you can pass to
customize the behavior of the MNIST classifier.

```bash
$ python trainer/train.py --help

Train a classifier on MNIST
flags:

trainer/train.py:
  --batch_size: training batch size.
    (default: '64')
    (an integer)
  --data_path: path to mnist npz file.
    (default: 'data/mnist.npz')
  --epochs: number of training epochs.
    (default: '10')
    (an integer)
  --job-dir: Catch job directory passed by cloud.
    (default: '')

Try --helpfull to get a list of all flags.c
```

## Tensorflow 2.0

If you want to try executing this code with Tensorflow 2.0, switch over to the
TF2 version of the installation and try running the code again:

```bash
pip install .[tf2]
python trainer/train.py --job-dir $JOB_DIR
```

The output should be the same. When you're done, switch back to the tf1
dependencies to continue with the tutorial:

```bash
pip install .[local]
```

## GCloud Local Mode

The next step up is to use the gcloud command line interface to run the job
locally. I'm not sure that this gains you much in the vanilla case - for
distributed training tasks I believe you get more feedback on whether or not
your arguments are correct.

One big benefit is that your job will output the logs and files needed to view
your model in tensorboard.

Try training your model again (remember, this will only work with Tensorflow
1.0):

```bash
JOB_DIR="output-dist"

gcloud ai-platform local train \
    --job-dir $JOB_DIR \
    --module-name trainer.train \
    --package-path trainer
```

## Local Tensorboard

The above command will generate the logs that Tensorboard needs to show off
model info and graphs.

To run Tensorboard locally, run the following command in your terminal:

```bash
tensorboard --logdir $JOB_DIR --host=localhost
```

This will start a web interface you can visit at <http://localhost:6006/> to see
details of your model run.

# Running in Cloud

Next we'll run the same model in the cloud, in CPU and in GPU mode.

## Setup for Cloud

Before we can train models we'll have to set up the cloud environment with a
project and credentials. First, follow the instructions
[here](https://cloud.google.com/ml-engine/docs/tensorflow/getting-started-keras)
to get set up with:

-   a Cloud project,
-   your very own Cloud bucket,
-   the Google Cloud SDK, and
-   the required credentials to interact with Cloud from your local machine.

By the time you're through you should have the following environment variables
set:

```bash
export PROJECT_ID=<your cloud project>
export BUCKET_NAME=<name of your bucket>
export REGION="us-central1" # Unless you have some great reason to choose another
```

### Move MNIST data to your cloud bucket

From the `cloud_tutorial` directory, run the following command:

```bash
DATA_PATH="gs://$BUCKET_NAME/data/mnist.npz" bash -c 'gsutil cp data/mnist.npz $DATA_PATH'
```

You'll only have to do this a single time to stage the data for every subsequent
run.

## Submit via command line

This example submits the model training job to AI Platform, where it will
execute using CPUs. More more info on the command's arguments, see this
[AI platform page](https://cloud.google.com/sdk/gcloud/reference/ai-platform/jobs/submit/training).

This page gives more detail on job submission via the command line and via a
python programmatic interface, which we'll cover in the final example.
https://cloud.google.com/ml-engine/docs/training-jobs#formatting_your_configuration_parameters

From the `cloud_tutorial` directory, run:

```bash
JOB_NAME="MNIST_training_cpu_${USER}_$(date +%Y%m%d_%H%M%S)"
JOB_DIR="gs://$BUCKET_NAME/mnist_demo"

gcloud ai-platform jobs submit training $JOB_NAME \
  --job-dir $JOB_DIR \
  --staging-bucket gs://$BUCKET_NAME \
  --module-name trainer.train \
  --package-path trainer \
  --region $REGION \
  --runtime-version 1.14 \
  --python-version 3.5 \
  -- \
  --data_path $DATA_PATH \
  --job_name $JOB_NAME
```

You'll be able to see your job running at the
https://console.cloud.google.com/ai-platform/jobs dashboard. You can also stream
the logs directly to the terminal by running:

```bash
gcloud ai-platform jobs stream-logs $JOB_NAME
```

## Cloud Tensorboard

Your local Tensorboard instance can see logs written to your bucket by Cloud.
Start tensorboard at the command line like you did before:

```bash
tensorboard --logdir $JOB_DIR --host=localhost
```

The page will look roughly the same, of course, but under the "TOGGLE ALL RUNS"
button on the bottom left you'll see a `gs://` prefix on the log directory.
Proof achieved!

## Submit a GPU job

The GPU training code is the same - the only difference is the cloud environment
in which the job executes. The GPU environment installs the

For the GPU job you will need to make sure you have quota in `$REGION`. The
following example executes with P100 GPUs.

To submit a GPU job, run the following command from the `cloud_tutorial` root:

```bash
JOB_NAME="MNIST_training_GPU_${USER}_$(date +%Y%m%d_%H%M%S)"
JOB_DIR="gs://$BUCKET_NAME/mnist_demo"

gcloud ai-platform jobs submit training $JOB_NAME \
  --job-dir $JOB_DIR \
  --staging-bucket gs://$BUCKET_NAME \
  --module-name trainer.train \
  --package-path trainer \
  --region $REGION\
  --scale-tier custom \
  --master-machine-type standard_p100 \
  --runtime-version 1.14 \
  --python-version 3.5 \
  -- \
  --data_path $DATA_PATH \
  --job_name $JOB_NAME
```

As before, you can stream the output of the logs with this command:

```bash
gcloud ai-platform jobs stream-logs $JOB_NAME
```

You can reload Tensorboard to see the new GPU model run, and verify that GPUs
were used by:

1.  Clicking on the "Graphs" menu item at the top of the screen
2.  Selecting your GPU run from the "Runs" dropdown on the left
3.  Clicking "Device" in the Color menu.

You should see that many of the nodes are colored blue, which is keyed "GPU" in
the legend on the left. Select the CPU run to verify that this is NOT the case.

This page gives more info on using GPUs with ML Engine:
https://cloud.google.com/ml-engine/docs/using-gpus

## Submit via python api (CURRENTLY BROKEN)

The file `submit.py` contains an example GPU submission using the Python api.
Run the following, again from `cloud_tutorial`:

```bash
sudo apt-get install google-cloud-sdk-app-engine-python
pip install google-api-python-client google-cloud-storage oauth2client

python submit.py \
  --bucket gs://$BUCKET_NAME \
  --project_id $PROJECT_ID \
  --region $REGION
```

## Other Tutorials

Cloud platform's
[Getting Started with Keras](https://cloud.google.com/ml-engine/docs/tensorflow/getting-started-keras)
and
[Getting Started with Tensorflow Estimator](https://cloud.google.com/ml-engine/docs/tensorflow/getting-started-training-prediction)
both have similar structures to this tutorial; all of the supporting Cloud and
python configuration is the same, so feel free to head to these tutorials next
to get some different experience with the platform.

## Docker

This is the next phase. Currently, running `./submit.sh local` will actually
work.

Some notes:

-   Each project on Google Cloud has its own Container registry:
    https://pantheon.corp.google.com/gcr/images/research-3141

## Caliban

To note:

-   flagfile works!
-   convert to abseil logging, vs using the local stuff.
