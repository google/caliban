"""Command line parser for the Caliban app.

"""
import sys
from argparse import REMAINDER
from typing import Any, Dict, List, Optional, Union

from absl.flags import argparse_flags
from blessings import Terminal

import caliban.cloud.types as ct
import caliban.config as conf
import caliban.util as u
from caliban import __version__

t = Terminal()


def _job_mode(use_gpu: bool, gpu_spec: Optional[ct.GPUSpec],
              tpu_spec: Optional[ct.TPUSpec]) -> conf.JobMode:
  """Encapsulates the slightly-too-complicated logic around the default job mode
  to choose based on the values of three incoming parameters.

  """
  if not use_gpu and gpu_spec is not None:
    # This should never happen, due to our CLI validation.
    raise AssertionError("gpu_spec isn't allowed for CPU only jobs!")

  # Base mode.
  mode = conf.JobMode.GPU if use_gpu else conf.JobMode.CPU

  # For the specific case where there's no GPU specified and a TPU is, set the
  # mode back to CPU and don't attach a GPU.
  if gpu_spec is None and tpu_spec is not None:
    mode = conf.JobMode.CPU

  return mode


def resolve_job_mode(args: Dict[str, Any]) -> conf.JobMode:
  """Similar to job_mode above; plucks the values out of a parsed CLI arg map vs
  taking them directory.

  """
  use_gpu = args["use_gpu"]
  gpu_spec = args.get("gpu_spec")
  tpu_spec = args.get("tpu_spec")
  return _job_mode(use_gpu, gpu_spec, tpu_spec)


def validate_script_args(argv: List[str], items: List[str]) -> List[str]:
  """This validation catches errors where argparse slurps up anything after the
  required argument as a script_arg, EVEN if it's not separated by a --.

  We do this instead of just parsing them directly so that we can still have a
  nice help string provided by argparse.

  """

  # items before the double-dashes, expected script_args after.
  pre_args, expected = u.split_by(argv, "--")
  if items == expected:
    return items

  # get the extra arguments parsed BEFORE the dash. These were probably meant
  # to be options to caliban itself.
  pre_dashes, _ = u.split_by(items, "--")

  joined = ' '.join(pre_dashes)
  expected_s = ' '.join(expected)

  # caliban arguments before these unexpected arguments.
  before_pre_dashes = pre_args[:-len(pre_dashes)]

  pwas = 'was' if len(pre_dashes) == 1 else 'were'
  parg = 'argument' if len(pre_dashes) == 1 else 'arguments'

  u.err(f"\nThe {parg} '{joined}' {pwas} supplied after required arguments \
but before the '--' separator and {pwas} not properly parsed.\n\n")
  u.err(f"if you meant to pass these as script_args, try \
moving them after the --, like this:\n\n")
  u.err(f"caliban {' '.join(before_pre_dashes)} -- {joined} {expected_s}\n\n")
  u.err(f"Otherwise, if these are in fact caliban keyword arguments, \
please move them before the python module name argument.\n\n")
  sys.exit(1)


def add_script_args(parser):
  """Adds an argument group that, paired with the validation above, slurps up all
  arguments provided after a '--'.

  """
  parser.add_argument_group('pass-through arguments').add_argument(
      "script_args",
      nargs=REMAINDER,
      default=[],
      metavar="-- YOUR_ARGS",
      help=
      """This is a catch-all for arguments you want to pass through to your script.
any arguments after '--' will pass through.""")


def require_module(parser):
  parser.add_argument("module",
                      type=u.validated_package,
                      help="Code to execute, in either \
'trainer.train' or 'trainer/train.py' format.")


def setup_extras(parser):
  parser.add_argument("--extras",
                      action="append",
                      help="setup.py dependency keys.")


def docker_run_arg(parser):
  """Adds a command that accepts arguments to pass directly to `docker run`.

  """
  parser.add_argument("--docker_run_args",
                      type=lambda s: s.split(" "),
                      help="String of args to add to Docker.")


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
Must be one of {regions}. \
(Defaults to $REGION or '{conf.DEFAULT_REGION.value}'.)")


def image_tag_arg(parser):
  parser.add_argument(
      "--image_tag",
      help=f"Docker image tag accessible via Container Registry. If supplied, \
Caliban will skip the build and push steps and use this image tag.")


def machine_type_arg(parser):
  machine_types = u.enum_vals(ct.MachineType)
  cpu_default = conf.DEFAULT_MACHINE_TYPE[conf.JobMode.CPU].value
  gpu_default = conf.DEFAULT_MACHINE_TYPE[conf.JobMode.GPU].value

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


def building_parser(base):
  """Augments the supplied base with options required by any parser that builds a
  docker image.

  """
  base_parser(base)
  require_module(base)
  extra_dirs(base)


def executing_parser(base):
  """Augments the supplied base with options required by any parser that executes
  code vs running some interactive process.

  """
  building_parser(base)
  add_script_args(base)


def shell_parser(base):
  """Configure the Shell subparser."""
  parser = base.add_parser(
      'shell', help='Start an interactive shell with this dir mounted.')
  base_parser(parser)
  docker_run_arg(parser)
  parser.add_argument(
      "--bare",
      action="store_true",
      help="Skip mounting the $HOME directory; load a bare shell.")


def notebook_parser(base):
  """Configure the notebook subparser."""
  parser = base.add_parser('notebook',
                           help='Run a local Jupyter notebook instance.')
  base_parser(parser)
  docker_run_arg(parser)

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


def local_build_parser(base):
  """Configure the subparser for `caliban run`."""
  parser = base.add_parser(
      'build',
      help='Build a Docker image without submitting or running any code.')
  building_parser(parser)


def local_run_parser(base):
  """Configure the subparser for `caliban run`."""
  parser = base.add_parser('run', help='Run a job inside a Docker container.')
  executing_parser(parser)
  docker_run_arg(parser)


def cloud_parser(base):
  """Configure the cloud subparser."""
  parser = base.add_parser('cloud', help='Submit AI platform jobs to Cloud.')
  executing_parser(parser)

  image_tag_arg(parser)
  project_id_arg(parser)
  region_arg(parser)
  machine_type_arg(parser)

  parser.add_argument(
      "--gpu_spec",
      metavar=ct.GPUSpec.METAVAR,
      type=ct.GPUSpec.parse_arg,
      help=f"Type and number of GPUs to use for each AI Platform submission. \
Defaults to 1x{conf.DEFAULT_GPU.name} in GPU mode or None if --nogpu is passed."
  )

  parser.add_argument("--tpu_spec",
                      metavar=ct.TPUSpec.METAVAR,
                      type=ct.TPUSpec.parse_arg,
                      help=f"Type and number of TPUs to request for each \
AI Platform submission. Defaults to None.")

  parser.add_argument(
      "--force",
      action="store_true",
      help="Force past validations and submit the job as specified.")

  parser.add_argument("--name", help="Set a job name for AI Platform jobs.")

  parser.add_argument(
      "--experiment_config",
      type=conf.load_experiment_config,
      help="Path to an experiment config, or 'stdin' to read from stdin.")

  parser.add_argument("-l",
                      "--label",
                      metavar="KEY=VALUE",
                      action="append",
                      type=u.parse_kv_pair,
                      help="Extra label k=v pair to submit to Cloud.")

  parser.add_argument(
      conf.DRY_RUN_FLAG,
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
  local_build_parser(subparser)
  local_run_parser(subparser)
  cloud_parser(subparser)
  return parser


# Validations that require access to multiple arguments at once.


def mac_gpu_check(job_mode: conf.JobMode, command: str) -> None:
  """If the command depends on 'docker run' and is running on a Mac, fail
fast.

  """
  if conf.gpu(job_mode) and command in ("shell", "notebook", "run"):
    u.err(
        f"\n'caliban {command}' doesn't support GPU usage on Macs! Please pass \
--nogpu to use this command.\n\n")
    u.err(
        "(GPU mode is fine for 'caliban cloud' from a Mac; just nothing that runs \
locally.)\n\n")
    sys.exit(1)


def _validate_no_gpu_type(use_gpu: bool, gpu_spec: Optional[ct.GPUSpec]):
  """Prevents a user from submitting a Cloud job using a CPU image when they've
  explicitly attempted to set a GPU spec.

  """
  gpu_disabled = not use_gpu
  if gpu_disabled and gpu_spec is not None:
    u.err(f"\n'--nogpu' is incompatible with an explicit --gpu_spec option. \
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
      u.err(f"\n'{machine_type.value}' isn't a valid machine type \
for {gpu_spec.count} {gpu_spec.gpu.name} GPUs.\n\n")
      u.err(ct.with_gpu_advice_suffix(f"Try one of these: {allowed}"))
      u.err("\n")
      sys.exit(1)


def _validate_accelerator_region(spec: Optional[Union[ct.GPUSpec, ct.TPUSpec]],
                                 region: ct.Region):
  """Check that the supplied region is valid for the accelerator specification,
  if supplied.

  """
  if spec is not None:
    accel = spec.accelerator_type

    if not spec.valid_region(region):
      # Show a list of the allowed types, sorted so that at least the machine
      # prefixes stick together.
      allowed = u.enum_vals(spec.allowed_regions())
      allowed.sort()
      u.err(f"\n'{region.value}' isn't a valid region \
for {accel}s of type {spec.name}.\n\n")
      u.err(f"Try one of these: {allowed}\n\n")
      u.err(f"See this page for more info about regional \
support for {accel}s: https://cloud.google.com/ml-engine/docs/regions \n")
      sys.exit(1)


def validate_across_args(args) -> None:
  """Apply validations that need combinations of arguments to work."""
  m = vars(args)

  command = m["command"]

  if u.is_mac():
    job_mode = resolve_job_mode(m)
    mac_gpu_check(job_mode, command)

  if command == "cloud" and not m.get("force"):
    use_gpu = m.get("use_gpu")
    region = conf.extract_region(vars(args))
    gpu_spec = args.gpu_spec
    tpu_spec = args.tpu_spec

    _validate_no_gpu_type(use_gpu, gpu_spec)

    # A TPU is valid with or without an attached GPU.
    _validate_accelerator_region(tpu_spec, region)

    if use_gpu:
      _validate_machine_type(gpu_spec, args.machine_type)
      _validate_accelerator_region(gpu_spec, region)

  return args


def parse_flags(argv):
  """Function required by absl.app.run. Internally generates a parser and returns
  the results of parsing caliban arguments.

  """
  args = argv[1:]
  ret = caliban_parser().parse_args(args)

  # Validate that extra script args were properly parsed.
  validate_script_args(args, vars(ret).get('script_args', []))

  return validate_across_args(ret)
