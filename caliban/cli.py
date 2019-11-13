"""
CLI utilities.
"""
from argparse import REMAINDER, ONE_OR_MORE

from absl.flags import argparse_flags


# pylint: disable=redefined-builtin
def boolean_arg(parser, flag, default, help=None, **kwargs):
  """Parses booleans closer to the style of Abseil.
  """
  parser.add_argument(f"--{flag}",
                      action="store_true",
                      default=default,
                      help=f"{help} (defaults to {default}.)",
                      **kwargs)
  parser.add_argument(f"--no{flag}",
                      dest=f"{flag}",
                      help=f"explicitly set {flag} to False.",
                      action="store_false")


def add_script_args(parser):
  parser.add_argument_group('pass-through arguments').add_argument(
      "script_args",
      nargs=REMAINDER,
      default=[],
      help=
      """This is a catch-all for arguments you want to pass through to your script.
any unfamiliar arguments will just pass right through.""")


def require_module(parser):
  # TODO validate that this actually exists on the filesystem.
  parser.add_argument("-p",
                      "--package_path",
                      required=True,
                      help="Path to your code.")
  parser.add_argument("-m",
                      "--module",
                      required=True,
                      help="Local module to run.")


def setup_extras(parser):
  parser.add_argument("-e",
                      "--extras",
                      nargs=ONE_OR_MORE,
                      help="setup.py dependency keys.")


def gpu_flag(parser):
  boolean_arg(parser, "GPU", False, help="Set to enable GPU usage.")


def parse_flags(argv):
  """Internally generates a parser and parses the supplied argument from invoking
the app.

  Note - this """
  parser = argparse_flags.ArgumentParser(description="""
Docker and AI Platform model training and development script.
    """,
                                         prog="caliban")

  subdocker = parser.add_subparsers(dest="command")

  # Create a shell.
  shell = subdocker.add_parser(
      'shell', help='Start an interactive shell with this dir mounted.')
  gpu_flag(shell)
  setup_extras(shell)

  # Run directly.
  run = subdocker.add_parser('run', help='Run a job inside a Docker container.')
  gpu_flag(run)
  setup_extras(run)

  run_named = run.add_argument_group('required named arguments')
  require_module(run_named)
  add_script_args(run)

  # Cloud submission
  cloud = subdocker.add_parser('cloud',
                               help='Submit the docker container to Cloud.')
  gpu_flag(cloud)
  setup_extras(cloud)
  boolean_arg(cloud,
              "stream_logs",
              True,
              help="Set to stream logs after job submission.")

  cloud_named = cloud.add_argument_group('required named arguments')
  require_module(cloud_named)
  add_script_args(cloud)

  # Cloud submission
  notebook = subdocker.add_parser('notebook', help='Generate Jupyterlab.')
  gpu_flag(notebook)
  setup_extras(notebook)

  return parser.parse_args(argv[1:])
