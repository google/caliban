"""Command line parser for the Caliban app.

"""
import sys
from argparse import REMAINDER
from typing import Optional

from absl.flags import argparse_flags

import caliban.cloud as c
import caliban.cloud.types as ct
import caliban.config as conf
import caliban.util as u
from caliban import __version__


def add_script_args(parser):
  """Adds an argument group that slurps up all arguments provided after a '--'.

  TODO this is broken in that it will start accepting arguments after ANY
  unrecognized string. This means that if you provide keyword args after the
  module you want to run, for example, they'll be interpreted as script args
  and not used by Caliban.

  We want the docstring this option provides but not the implementation.

  """
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
                      help="Code to execute, in either \
'trainer.train' or 'trainer/train.py' format.")


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
      help="Extra directories to include. List these from large to small \
to take full advantage of Docker's build cache.")


def no_gpu_flag(parser):
  parser.add_argument("--nogpu",
                      dest="use_gpu",
                      help="Disable GPU mode and force CPU-only.",
                      action="store_false")


def project_id_arg(parser):
  parser.add_argument(
      "--project_id",
      help="ID of the GCloud AI Platform project to use for Cloud job \
submission and image persistence. (Defaults to $PROJECT_ID; errors if \
both the argument and $PROJECT_ID are empty.)")


def region_arg(parser):
  regions = u.enum_vals(ct.valid_regions())
  parser.add_argument(
      "--region",
      type=ct.parse_region,
      help=f"Region to use for Cloud job submission and image persistence. \
Must be one of {regions}. (Defaults to $REGION or '{c.DEFAULT_REGION.value}'.)")


def machine_type_arg(parser):
  machine_types = u.enum_vals(ct.MachineType)
  cpu_default = c.DEFAULT_MACHINE_TYPE[c.JobMode.CPU].value
  gpu_default = c.DEFAULT_MACHINE_TYPE[c.JobMode.GPU].value

  parser.add_argument("--machine_type",
                      type=ct.parse_machine_type,
                      help=f"Cloud machine type to request. Must be one of \
{machine_types}. Defaults to '{gpu_default}' in GPU mode, or '{cpu_default}' \
if --nogpu is passed.")


# Parsers for each command supported by Caliban.


def base_parser(base):
  "Configures options that every command needs."
  no_gpu_flag(base)
  setup_extras(base)


def executing_parser(base):
  """Augments the supplied base with options required by any parser that executes
  code vs running some interactive process.

  """
  base_parser(base)
  require_module(base)
  extra_dirs(base)
  add_script_args(base)


def shell_parser(base):
  """Configure the Shell subparser."""
  parser = base.add_parser(
      'shell', help='Start an interactive shell with this dir mounted.')
  base_parser(parser)
  parser.add_argument(
      "--bare",
      action="store_true",
      help="Skip mounting the $HOME directory; load a bare shell.")


def notebook_parser(base):
  """Configure the notebook subparser."""
  parser = base.add_parser('notebook',
                           help='Run a local Jupyter notebook instance.')
  base_parser(parser)

  # Custom notebook arguments.
  parser.add_argument(
      "-p",
      "--port",
      type=int,
      help="Port to use for Jupyter, inside container and locally.")
  parser.add_argument("-jv",
                      "--jupyter_version",
                      help="Jupyterlab version to install via pip.")
  parser.add_argument(
      "--lab",
      action="store_true",
      help="run 'jupyter lab', vs the default 'jupyter notebook'.")
  parser.add_argument(
      "--bare",
      action="store_true",
      help="Skip mounting the $HOME directory; run an isolated Jupyter lab.")


def local_run_parser(base):
  """Configure the subparser for `caliban run`."""
  parser = base.add_parser('run', help='Run a job inside a Docker container.')
  executing_parser(parser)


def cloud_parser(base):
  """Configure the cloud subparser."""
  parser = base.add_parser('cloud', help='Submit AI platform jobs to Cloud.')
  executing_parser(parser)

  # Custom cloud arguments.

  project_id_arg(parser)
  region_arg(parser)
  machine_type_arg(parser)

  parser.add_argument(
      "--gpu_spec",
      metavar=ct.GPUSpec.METAVAR,
      type=ct.GPUSpec.parse_arg,
      help=f"Type and number of GPUs to use for each AI Platform submission. \
Defaults to 1x{c.DEFAULT_GPU.name} in GPU mode or None if --nogpu is passed.")

  parser.add_argument(
      "--force",
      action="store_true",
      help="Force past validations and submit the job as specified.")

  parser.add_argument("--name", help="Set a job name for AI Platform jobs.")

  parser.add_argument("--experiment_config",
                      type=u.compose(
                          conf.validate_experiment_config,
                          u.compose(conf.valid_json, u.validated_file)),
                      help="Path to an experiment config.")

  parser.add_argument("-l",
                      "--label",
                      metavar="KEY=VALUE",
                      action="append",
                      type=u.parse_kv_pair,
                      help="Extra label k=v pair to submit to Cloud.")

  parser.add_argument(
      c.DRY_RUN_FLAG,
      action="store_true",
      help="Don't actually submit; log everything that's going to happen.")


def caliban_parser():
  """Creates and returns the argparse instance for the entire Caliban app."""

  parser = argparse_flags.ArgumentParser(description=f"""Docker and AI
  Platform model training and development script. For detailed
  documentation, visit the Git repo at
  https://team.git.corp.google.com/blueshift/caliban/ """,
                                         prog="caliban")
  parser.add_argument('--version',
                      action='version',
                      version=f"%(prog)s {__version__}")

  subparser = parser.add_subparsers(dest="command")
  subparser.required = True

  shell_parser(subparser)
  notebook_parser(subparser)
  local_run_parser(subparser)
  cloud_parser(subparser)
  return parser


# Validations that require access to multiple arguments at once.


def mac_gpu_check(mode: str, use_gpu: bool) -> None:
  """If the command depends on 'docker run' and is running on a Mac, fail
fast.

  """
  if use_gpu and mode in ("shell", "notebook", "run"):
    sys.stderr.write(
        f"\n'caliban {mode}' doesn't support GPU usage on Macs! Please pass \
--nogpu to use this command.\n\n")
    sys.stderr.write(
        "(GPU mode is fine for 'caliban cloud' from a Mac; just nothing that runs \
locally.)\n\n")
    sys.exit(1)


def _validate_no_gpu_type(use_gpu: bool, gpu_spec: Optional[ct.GPUSpec]):
  """Prevents a user from submitting a Cloud job using a CPU image when they've
  explicitly attempted to set a GPU spec.

  """
  gpu_disabled = not use_gpu
  if gpu_disabled and gpu_spec is not None:
    sys.stderr.write(
        f"\n'--nogpu' is incompatible with an explicit --gpu_spec option. \
Please remove one or the other!\n\n")
    sys.exit(1)


def _validate_machine_type(gpu_spec: Optional[ct.GPUSpec],
                           machine_type: Optional[ct.MachineType]):
  """If both args are provided,makes sure that Cloud supports this particular
  combination of GPU count, type and machine type.

  """
  if gpu_spec is not None and machine_type is not None:
    if not gpu_spec.valid_machine_type(machine_type):
      # Show a list of the allowed types, sorted so that at least the machine
      # prefixes stick together.
      allowed = u.enum_vals(gpu_spec.allowed_machine_types())
      allowed.sort()
      sys.stderr.write(f"\n'{machine_type.value}' isn't a valid machine type \
for {gpu_spec.count} {gpu_spec.gpu.name} GPUs.\n\n")
      sys.stderr.write(
          ct.with_gpu_advice_suffix(f"Try one of these: {allowed}"))
      sys.stderr.write("\n")
      sys.exit(1)


def _validate_gpu_region(spec: Optional[ct.GPUSpec], region: ct.Region):
  """Check that the supplied region is valid for the GPUSpec, if supplied."""
  if spec is not None:
    if not spec.valid_region(region):
      # Show a list of the allowed types, sorted so that at least the machine
      # prefixes stick together.
      allowed = u.enum_vals(spec.allowed_regions())
      allowed.sort()
      sys.stderr.write(f"\n'{region}' isn't a valid region \
for GPUs of type {spec.gpu.name}.\n\n")
      sys.stderr.write(f"Try one of these: {allowed}\n\n")
      sys.stderr.write(f"See this page for more info about regional \
support for GPUs: https://cloud.google.com/ml-engine/docs/regions \n")
      sys.exit(1)


def validate_across_args(args) -> None:
  """Apply validations that need combinations of arguments to work."""
  m = vars(args)

  command = m["command"]
  use_gpu = m.get("use_gpu")

  if u.is_mac():
    mac_gpu_check(command, use_gpu)

  if command == "cloud" and not m.get("force"):
    spec = args.gpu_spec
    _validate_no_gpu_type(use_gpu, spec)
    if use_gpu:
      region = conf.extract_region(vars(args))
      _validate_machine_type(spec, args.machine_type)
      _validate_gpu_region(spec, region)

  return args


def parse_flags(argv):
  """Function required by absl.app.run. Internally generates a parser and returns
  the results of parsing caliban arguments.

  """
  ret = caliban_parser().parse_args(argv[1:])
  return validate_across_args(ret)
