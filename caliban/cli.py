"""
CLI utilities.
"""
from argparse import REMAINDER

from absl.flags import argparse_flags

import caliban.util as u


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
  parser.add_argument("module",
                      type=u.validated_package,
                      help="Local module to run.")


def setup_extras(parser):
  parser.add_argument("-e",
                      "--extras",
                      action="append",
                      help="setup.py dependency keys.")


def extra_dirs(parser):
  parser.add_argument(
      "-d",
      "--dir",
      action="append",
      type=u.validated_directory,
      help="Extra directories to include. Try to list these from big to small!")


def gpu_flag(parser):
  boolean_arg(parser, "gpu", True, help="Set to enable GPU usage.")


def shell_parser(base):
  """Configure the Shell subparser."""
  parser = base.add_parser(
      'shell', help='Start an interactive shell with this dir mounted.')
  gpu_flag(parser)
  setup_extras(parser)
  parser.add_argument(
      "--bare",
      action="store_true",
      help="Skip mounting the $HOME directory; load a bare shell.")


def notebook_parser(base):
  """Configure the notebook subparser."""
  parser = base.add_parser('notebook',
                           help='Run a local Jupyter notebook instance.')
  gpu_flag(parser)
  setup_extras(parser)
  parser.add_argument("-p",
                      "--port",
                      type=int,
                      help="Local port to use for Jupyter.")
  parser.add_argument("--lab",
                      action="store_true",
                      help="run Jupyterlab, vs just jupyter.")
  parser.add_argument(
      "--bare",
      action="store_true",
      help="Skip mounting the $HOME directory; run an isolated Jupyter lab.")


def local_run_parser(base):
  """Configure the subparser for `caliban run`."""
  parser = base.add_parser('run', help='Run a job inside a Docker container.')
  require_module(parser)
  extra_dirs(parser)
  gpu_flag(parser)
  setup_extras(parser)
  add_script_args(parser)


def cloud_parser(base):
  """Configure the cloud subparser."""
  parser = base.add_parser('cloud',
                           help='Submit the docker container to Cloud.')
  require_module(parser)
  parser.add_argument("--name", help="Set a job name to see in the cloud.")
  extra_dirs(parser)
  gpu_flag(parser)
  setup_extras(parser)
  parser.add_argument("-l",
                      "--label",
                      metavar="KEY=VALUE",
                      action="append",
                      type=u.parse_kv_pair,
                      help="Extra label k=v pair to submit to Cloud.")
  boolean_arg(parser,
              "stream_logs",
              False,
              help="Set to stream logs after job submission.")
  add_script_args(parser)


def caliban_parser():
  """Creates and returns the argparse instance for the entire Caliban app."""
  parser = argparse_flags.ArgumentParser(description=f"""Docker and AI
  Platform model training and development script. For detailed
  documentation, visit the Git repo at
  https://team.git.corp.google.com/blueshift/caliban/ """,
                                         prog="caliban")

  subparser = parser.add_subparsers(dest="command")
  shell_parser(subparser)
  notebook_parser(subparser)
  local_run_parser(subparser)
  cloud_parser(subparser)
  return parser


def parse_flags(argv):
  """Function required by absl.app.run. Internally generates a parser and returns
  the results of parsing caliban arguments.

  """
  return caliban_parser().parse_args(argv[1:])
