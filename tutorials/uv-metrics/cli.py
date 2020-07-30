"""CLI Interface for the UV-metrics tutorial example."""

import argparse

from absl.flags import argparse_flags


def create_parser():
  """Creates and returns the argparse instance for the experiment config
  expansion app.

  """

  parser = argparse_flags.ArgumentParser(
      formatter_class=argparse.ArgumentDefaultsHelpFormatter,
      description=
      f"""Configurable arguments for the uv-metrics Caliban tutorial.""",
      prog="python -m mnist")

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

  parser.add_argument("--learning_rate",
                      "--lr",
                      type=float,
                      default=0.01,
                      help="Learning rate.")
  parser.add_argument("--epochs", type=int, default=3, help="Epochs to train.")

  return parser


def parse_flags(argv):
  """Function required by absl.app.run. Internally generates a parser and returns
  the results of parsing hello-uv arguments.

  """
  args = argv[1:]
  return create_parser().parse_args(args)
