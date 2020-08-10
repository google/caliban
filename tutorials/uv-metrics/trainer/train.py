"""This module, and plot.py in the same folder, demonstrate how to use UV's
reporter and reader classes to collect data during a training run and then load
it again after the run for analysis.

"""

from __future__ import division, print_function

import getpass
from typing import Dict, Optional

import fs
import tensorflow as tf
import tensorflow_datasets as tfds
import tqdm
import uv
import uv.tensorflow.reporter as rft
import uv.util as u
from absl import app
from uv.fs.reporter import FSReporter
from uv.mlflow.reporter import MLFlowReporter

from trainer import cli

MNIST = "mnist"


def normalize(example):
  """This normalizes all color values to be between 0 and 1. This gets turned
  into a tensorflow operation... print statements will only get called a single
  time.

  """
  example['image'] = tf.cast(example['image'], tf.float32) / 255.
  return example


def prepare_mnist(
    batch_size: int,
    train_shuffle_buffer: int = 1000) -> Dict[str, tf.data.Dataset]:
  """Generates a dictionary with keys measure, train, test, all from mnist.

  https://www.tensorflow.org/datasets/catalog/mnist

  Training has 60k examples, while test has 10k examples.

  """
  train = tfds.load(MNIST, split=tfds.Split.TRAIN,
                    shuffle_files=True).map(normalize)
  test = tfds.load(MNIST, split=tfds.Split.TEST).map(normalize)

  return {
      # This will create a buffer of `train_shuffle_buffer` items in memory,
      # then sample from these to get samples. This biases toward the first
      # batch of examples. the "repeat" effectively lets you go forever.
      #
      # If you take enough batches to run out the epoch, you'll start pulling
      # from the beginning again.
      "batched": train.shuffle(train_shuffle_buffer).repeat().batch(batch_size),

      # These are the unbatched train and test sets, used for evaluation and
      # metric generation at the end of each batch.
      "train": train,
      "test": test
  }


def build_model(activation: str, width: int, depth: int) -> tf.keras.Model:
  """Return the bare model that we'll train."""
  out = inp = tf.keras.layers.Input(shape=(28, 28, 1))
  out = tf.keras.layers.Flatten()(out)

  # Stack a bunch of layers of the same width.
  for _ in range(depth):
    out = tf.keras.layers.Dense(width, activation=activation)(out)

  # Append a final layer that checks 10 classes.
  out = tf.keras.layers.Dense(10, activation=None)(out)

  # return the final model, all sewn together.
  return tf.keras.Model(inputs=inp, outputs=out)


@tf.function
def compute_loss(labels, logits):
  """Compute loss for a single batch of data, given the precomputed logits and
  expected labels. The returned loss is normalized by the batch size.

  """
  cur_batch_size = tf.cast(labels.shape[0], tf.float32)
  cce = tf.losses.SparseCategoricalCrossentropy(
      from_logits=True, reduction=tf.losses.Reduction.SUM)

  # loss here is the cce, normalized by the batch size.
  return cce(labels, logits) / cur_batch_size


@tf.function
def compute_accuracy(labels, logits):
  """Compute accuracy for a single batch of data, given the precomputed logits
  and expected labels. The returned accuracy is normalized by the batch size.

  """
  current_batch_size = tf.cast(labels.shape[0], tf.float32)

  # logits is the percent chance; this gives the category for each.
  predictions = tf.argmax(logits, axis=1)

  # return the average number of items equal to their label.
  return tf.reduce_sum(tf.cast(tf.equal(labels, predictions),
                               tf.float32)) / current_batch_size


@tf.function
def compute_batch_loss_acc(model, X, y, training: bool):
  """Compute the loss AND accuracy for the supplied batch; computations runs in
  sequence.

  """
  logits = model(X, training=training)
  loss = compute_loss(y, logits)
  acc = compute_accuracy(y, logits)

  # Return a pair of two numbers - average loss and accuracy for the given
  # batch.
  return loss, acc


def total_metrics(model, dataset, batch_size):
  """This function calculates loss and accuracy metrics for the entire supplied
  dataset. The computation is performed one batch at a time; the returned
  numbers are normalized by the full dataset's count.

  Returns a dict with "loss" and "accuracy" keys.

  """
  total_loss = 0
  total_acc = 0.
  total_samples = 0

  for batch in dataset.batch(batch_size):
    n = len(batch)
    images = batch['image']
    labels = batch['label']
    batch_loss, batch_acc = compute_batch_loss_acc(model,
                                                   images,
                                                   labels,
                                                   training=True)
    # NON-normalized quantities. Sum of all loss.
    total_loss += batch_loss * n
    total_acc += batch_acc * n
    total_samples += n

  # so this is the running total loss so far.
  total_loss /= total_samples
  total_acc /= total_samples

  # RUNNING average of total loss and accuracy.
  return {"loss": total_loss, "accuracy": total_acc}


@tf.function
def train_step(model, optimizer, X, y):
  """Training loop implementation; the training loop is custom so that we can
  compute loss and accuracy for each batch as we train, inside the loop.

  """
  with tf.GradientTape() as tape:
    logits = model(X, training=True)
    loss = compute_loss(y, logits)

  accuracy = compute_accuracy(y, logits)
  grads = tape.gradient(loss, model.trainable_variables)
  optimizer.apply_gradients(zip(grads, model.trainable_variables))
  return {"loss": loss, "accuracy": accuracy}


# Reporters


def gcloud_reporter(prefix: str, job_name: str):
  """Returns a reporter implementation that persists metrics in GCloud in jsonl
  format.

  NOTE this is almost identical to local_reporter... the only different is the
  strict=False option.

  """
  if prefix.endswith("/"):
    prefix = prefix[:-1]

  cloud_path = f"{prefix}/{job_name}?strict=False"
  gcsfs = fs.open_fs(cloud_path)
  return FSReporter(gcsfs).stepped()


def local_reporter(folder: str, job_name: str):
  """Returns a reporter implementation that persists metrics on the local
  filesystem in jsonl format.

  """
  local_path = fs.path.join(folder, job_name)
  return FSReporter(local_path).stepped()


def tensorboard_reporter(job_name: str):
  """Returns a reporter that sends scalar metrics over to tensorboard."""
  return rft.TensorboardReporter(f"tboard/{job_name}")


def build_reporters(
    job_name: str,
    m: Dict[str, float],
    local_path: Optional[str] = None,
    gcloud_path: Optional[str] = None,
    tensorboard_path: Optional[str] = None) -> Dict[str, uv.AbstractReporter]:
  """Returns a dict of namespace to reporter."""

  # This reporter keeps all metrics in an internal dictionary of metric name
  # (string) to a list of metric values.
  #
  # The "stepped()" function here is a convenience, here in the early days of
  # this library, that wraps every value that reaches the MemoryReporter - say,
  # the number 10.5 - in a dictionary that looks like
  #
  # {"step": step_idx, "value": 10.5}
  #
  # This lets you access the value of the step later.
  mem = uv.MemoryReporter(m).stepped()

  # The "tqdm()" function returns a LoggingReporter() implementation that's
  # able to log above a tqdm progress bar. If you simply called
  # r.LoggingReporter(), the reporter would log to sys.stdout.
  logging = uv.LoggingReporter.tqdm()

  mlf = MLFlowReporter()

  # This is a new, compound reporter. When you log to this compound reporter,
  # it will turn around and pass metrics to the memory and logging reporters.
  base = mem.plus(logging, mlf)

  # reporters that persist to disk. These are optional, so we overwrite base
  # only if local_path or gcloud_path are supplied.
  if local_path is not None:
    local = local_reporter(local_path, job_name)
    base = base.plus(local)

  # This reporter, if the gcloud_path is supplied, will log to a gcloud bucket.
  if gcloud_path is not None:
    gcloud = gcloud_reporter(gcloud_path, job_name)
    base = base.plus(gcloud)

  # See how easy it is to build non-trivial reporters? At this stage, we have a
  # reporter that is logging to four reporter implementations - an in-memory
  # version for immediate graphing (imagine a notebook usecase), a logging
  # version, and two separate filesystem instances.

  # Finally, let's append a tensorboard reporter if the user's supplied it:

  if tensorboard_path is not None:
    tboard = tensorboard_reporter(job_name)
    base = base.plus(tboard).map_values(lambda step, v: u.to_metric(v))

  # The final step here is to call "map_values" with a function that will
  # accept each step and value as it's reported, and transform the value before
  # passing into all of our underlying reporters. to_metric, in this case,
  # simply extracts the numpy() argument if it exists on the supplied value.
  # This allows you to report tensors directly without calling numpy() before
  # reporting them.
  base = base.map_values(lambda step, v: u.to_metric(v))

  # Here we return the base reporter itself, AND a convenient map of string to
  # a few new reporters. Each one will act just like base, except each will
  # prepend a different prefix onto any metric passed in.
  return base, {
      "test": base.with_prefix("test"),
      "train": base.with_prefix("train"),
      "model": base.with_prefix("model")
  }


def record_measurements(step: int, reporters: Dict[str, uv.AbstractReporter],
                        measure_batch_size: int, model, training_data,
                        test_data):
  """This function actually records various metrics.

  NOTE that all of these measurements could have been recorded on the same base
  reporter! The only reason to break up the measurement like this is for style
  reasons.

  """

  # This section calculates loss and accuracy on the full training set and reports it to the base reporter with a prefix of "train".
  train_m = total_metrics(model, training_data, measure_batch_size)
  reporters["train"].report_all(step, train_m)

  # This section calculates loss and accuracy on the full TEST set and reports
  # it to the base reporter with a prefix of "test".
  test_m = total_metrics(model, test_data, measure_batch_size)
  reporters["test"].report_all(step, test_m)

  # This measurement is on the model itself, so we report it to the base with a
  # "model" prefix.
  weight_norm_sqr = sum([tf.math.square(tf.norm(w)) for w in model.weights])
  reporters["model"].report(step, "w2", weight_norm_sqr)


def train_and_log(
    model,
    optimizer,
    batch_size=128,
    # this is equal to the ENTIRE test set, each time.
    measure_batch_size=10000,
    batches=5,
    measure_every=1,
    local_path: Optional[str] = None,
    gcloud_path: Optional[str] = None,
    tensorboard_path: Optional[str] = None):
  """Run the training loop on all data and record measurements as we go."""

  # Get the data downloaded and prepared, batched by the supplied batch size.
  data = prepare_mnist(batch_size)
  batched_training = data['batched']

  # These are the train and test sets, not batched at all. We have these for
  # metric reporting purposes.
  train = data['train']
  test = data['test']

  # This is equivalent to batched_training.take(batches), but wrapped with a
  # fancy progress bar.
  meter = tqdm.tqdm(batched_training.take(batches),
                    total=batches,
                    unit="batch",
                    desc="training")

  job_name = f"{getpass.getuser()}_{u.uuid()}"
  tqdm.tqdm.write(f"Job Name: {job_name}")

  # this is the mutable map where the MemoryReporter will keep its data.
  metrics = {}

  # This is the base reporter, plus the map of prefix => prefixed reporter. The
  # code below only uses the map to record measurements, but it could just as
  # easily have used base directly.
  base, reporters = build_reporters(job_name,
                                    metrics,
                                    local_path=local_path,
                                    gcloud_path=gcloud_path,
                                    tensorboard_path=tensorboard_path)

  def should_measure(step):
    """Returns true if we should trigger a measurement for the supplied step, false
    otherwise.

    """
    return step % measure_every == 0

  def measure(step):
    """This function gets our record_measurements function to happen only every so
    often. The reason to gate the measurement this way, vs using a filter_step
    call on the reporter itself, is that the calculation of data that we want
    to report at ALL takes a long time.

    """
    if should_measure(step):
      record_measurements(step, reporters, measure_batch_size, model, train,
                          test)

  # For good measure, we make two MORE reporter instances with new prefixes.
  # We'll use batch_reporter inside the training loop to record stats on the
  # training loop process itself.
  batch_reporter = reporters["train"].with_prefix("batch")

  # This is how we can gate the reporter itself, using filter_step. This will
  # get the same data as batch_reporter, but with a different prefix; it will
  # only send measurements down the line every measure_every steps.
  limited_batch = reporters["train"].filter_step(
      lambda s: s % measure_every == 0).with_prefix(
          f"batch_every_{measure_every}")

  # Get initial measurements on the randomized model's performance before we've
  # trained at all.
  measure(0)

  # enter the training loop.
  for (step, batch) in enumerate(meter, 1):

    # for every batch... go get the images and labels.
    images = batch['image']
    labels = batch['label']

    # Perform the training step, and get back loss and accuracy for the current
    # batch.
    metadata = train_step(model, optimizer, images, labels)

    # Perform measurements on the test and training steps, if we pass the gate.
    measure(step)

    # Now we ALSO report the batch training steps.
    batch_reporter.report_all(step, metadata)
    limited_batch.report_all(step, metadata)

  # Once the loop is over, close the reporter and return the final mutable
  # metric store for graphing in-process.
  base.close()
  return metrics


def model_main(activation='relu', width=1000, depth=2, lr=0.5, **kwargs):
  """Main method; this sequences the basic steps often

  - create the model and optimizer,
  - train and record metrics,
  - plot all metrics.

  """
  print(f'Building model with width = {width}, learning rate = {lr}')

  model = build_model(activation, width, depth)
  optimizer = tf.optimizers.SGD(lr)

  with uv.start_run() as r:

    MLFlowReporter().report_params({
        **kwargs,
        **{
            "depth": depth,
            "width": width,
            "lr": lr,
            "activation": activation
        }
    })

    train_and_log(model, optimizer, **kwargs)


def run_app(args):
  """Main function to run the Hello-UV app. Accepts a Namespace-type output of an
  argparse argument parser.

  """
  model_main(activation=args.activation,
             width=args.width,
             depth=args.depth,
             lr=args.learning_rate,
             local_path=args.local_path,
             gcloud_path=args.gcloud_path,
             tensorboard_path=args.tensorboard_path)


def main():
  app.run(run_app, flags_parser=cli.parse_flags)


if __name__ == '__main__':
  main()
