"""CLI Interface for the Hello-UV tutorial example."""

import argparse

from absl.flags import argparse_flags


def create_parser():
  """Creates and returns the argparse instance for the experiment config
  expansion app.

  """

  parser = argparse_flags.ArgumentParser(
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description=f"""Configurable arguments for the UV Metrics demo.""",
      prog="python -m trainer.train")

  parser.add_argument(
      "--gcloud_path",
      help=
      """Path for gcloud logs; if supplied, used for persisting logs. This must be of
      the form gs://BUCKET_NAME/subfolder. Logs will be stored in the supplied
      folder in a subfolder named after the current job run.""")

  parser.add_argument(
      "--local_path",
      help=
      """Path for gcloud logs; if supplied, this location on the local filesystem is
      used for persisting logs in jsonl format. The path can be relative. Logs
      will be stored in the supplied folder in a subfolder named after the
      current job run.""")

  parser.add_argument(
      "--tensorboard_path",
      help=
      """project-local path for tensorboard logs; if supplied, this location on the
      local filesystem is used for persisting logs that tensorboard can
      read.""")

  parser.add_argument("--activation",
                      help="""Activation strings. Choose from the options at
https://www.tensorflow.org/api_docs/python/tf/keras/activations""",
                      default="relu")
  parser.add_argument("--width",
                      type=int,
                      default=1000,
                      help="Width of the network to train.")
  parser.add_argument("--depth",
                      type=int,
                      default=2,
                      help="Depth of the network to train.")
  parser.add_argument("--learning_rate",
                      "--lr",
                      type=float,
                      default=0.1,
                      help="Learning rate to use while training.")

  return parser


def parse_flags(argv):
  """Function required by absl.app.run. Internally generates a parser and returns
  the results of parsing hello-uv arguments.

  """
  args = argv[1:]
  return create_parser().parse_args(args)
