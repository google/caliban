#!/usr/bin/python
#
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""This tutorial comes from the Tensorflow MNIST quickstart at
https://www.tensorflow.org/tutorials/quickstart/beginner.

"""
import warnings
from typing import Dict

import mlflow
import mlflow.keras
import tensorflow as tf
import uv.reporter as r
import uv.util as u
from absl import app
from uv.mlflow.reporter import MLFlowReporter

import cli

# The following function call is the only addition to code required to
# automatically log metrics and parameters to MLflow.
mlflow.keras.autolog()

warnings.filterwarnings("ignore", category=DeprecationWarning)


def build_reporters(m: Dict[str, float]) -> Dict[str, r.AbstractReporter]:
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
  mem = r.MemoryReporter(m).stepped()

  # The "tqdm()" function returns a LoggingReporter() implementation that's
  # able to log above a tqdm progress bar. If you simply called
  # r.LoggingReporter(), the reporter would log to sys.stdout.
  logging = r.LoggingReporter.tqdm()

  mlf = MLFlowReporter()

  # This is a new, compound reporter. When you log to this compound reporter,
  # it will turn around and pass metrics to the memory and logging reporters.
  base = mem.plus(logging, mlf)

  # The final step here is to call "map_values" with a function that will
  # accept each step and value as it's reported, and transform the value before
  # passing into all of our underlying reporters. to_metric, in this case,
  # simply extracts the numpy() argument if it exists on the supplied value.
  # This allows you to report tensors directly without calling numpy() before
  # reporting them.
  return base.map_values(lambda step, v: u.to_metric(v))


def get_keras_model(width=128, activation='relu'):
  """Returns an instance of a Keras Sequential model.
https://www.tensorflow.org/api_docs/python/tf/keras/Sequential"""
  return tf.keras.models.Sequential([
      tf.keras.layers.Flatten(input_shape=(28, 28)),
      tf.keras.layers.Dense(width, activation=activation),
      tf.keras.layers.Dense(width, activation=activation),
      tf.keras.layers.Dense(10, activation=None),
  ])


def model_main(learning_rate=0.01, epochs=3, **kwargs):
  """Train a model against the MNIST dataset and print performance metrics."""
  mnist = tf.keras.datasets.mnist

  (x_train, y_train), (x_test, y_test) = mnist.load_data()
  x_train, x_test = x_train / 255.0, x_test / 255.0

  model = get_keras_model()

  loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
  optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)

  model.compile(optimizer=optimizer, loss=loss_fn, metrics=['accuracy'])

  # this is the mutable map where the MemoryReporter will keep its data.
  metrics = {}
  base = build_reporters(metrics)

  with mlflow.start_run():
    mlflow.log_params({
        **kwargs,
        **{
            "learning_rate": learning_rate,
            "epochs": epochs
        }
    })
    print(
        f'Training model with learning rate={learning_rate} for {epochs} epochs.'
    )
    model.fit(x_train, y_train, epochs=epochs)

    print('Model performance: ')
    score, accuracy = model.evaluate(x_test, y_test)
    mlflow.log_params({"final_score": score, "accuracy": accuracy})


def run_app(args):
  """Main function to begin training."""
  model_main(learning_rate=args.learning_rate,
             epochs=args.epochs,
             local_path=args.local_path,
             gcloud_path=args.gcloud_path,
             tensorboard_path=args.tensorboard_path)


def main():
  app.run(run_app, flags_parser=cli.parse_flags)


if __name__ == '__main__':
  main()
