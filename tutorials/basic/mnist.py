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

import tensorflow as tf
from absl import app, flags

warnings.filterwarnings("ignore", category=DeprecationWarning)

FLAGS = flags.FLAGS

# Define a command-line argument using the Abseil library:
# https://abseil.io/docs/python/guides/flags
flags.DEFINE_float('learning_rate', 0.1, 'Learning rate.')
flags.DEFINE_integer('epochs', 3, 'Epochs to train.')


def get_keras_model(width=128, activation='relu'):
  """Returns an instance of a Keras Sequential model.
https://www.tensorflow.org/api_docs/python/tf/keras/Sequential"""
  return tf.keras.models.Sequential([
      tf.keras.layers.Flatten(input_shape=(28, 28)),
      tf.keras.layers.Dense(width, activation=activation),
      tf.keras.layers.Dense(width, activation=activation),
      tf.keras.layers.Dense(10, activation=None),
  ])


def main(_):
  """Train a model against the MNIST dataset and print performance metrics."""
  mnist = tf.keras.datasets.mnist

  (x_train, y_train), (x_test, y_test) = mnist.load_data()
  x_train, x_test = x_train / 255.0, x_test / 255.0

  model = get_keras_model()

  loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(from_logits=True)
  optimizer = tf.keras.optimizers.Adam(learning_rate=FLAGS.learning_rate)

  model.compile(optimizer=optimizer, loss=loss_fn, metrics=['accuracy'])

  print(
      f'Training model with learning rate={FLAGS.learning_rate} for {FLAGS.epochs} epochs.'
  )
  model.fit(x_train, y_train, epochs=FLAGS.epochs)

  print('Model performance: ')
  model.evaluate(x_test, y_test, verbose=2)


if __name__ == '__main__':
  app.run(main)
