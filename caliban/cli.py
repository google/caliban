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
"""Command line parser for the Caliban app."""
import argparse
import os
import sys
from argparse import REMAINDER
from typing import Any, Dict, List, Optional, Union

import google.auth._cloud_sdk as csdk
from absl.flags import argparse_flags

import caliban.config as conf
import caliban.config.experiment as ce
import caliban.docker.build as b
import caliban.platform.cloud.types as ct
import caliban.platform.gke as gke
import caliban.platform.gke.constants as gke_k
import caliban.platform.gke.types as gke_t
import caliban.platform.gke.util as gke_u
import caliban.util as u
import caliban.util.argparse as ua
import caliban.util.schema as us
from caliban import __version__


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
  use_gpu = args.get("use_gpu", True)
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

  joined = " ".join(pre_dashes)
  expected_s = " ".join(expected)

  # caliban arguments before these unexpected arguments.
  before_pre_dashes = pre_args[:-len(pre_dashes)]

  pwas = "was" if len(pre_dashes) == 1 else "were"
  parg = "argument" if len(pre_dashes) == 1 else "arguments"

  u.err(
      """\nThe {} '{}' {} supplied after required arguments but before the '--' separator and {} not properly parsed.\n\n"""
      .format(parg, joined, pwas, pwas))
  u.err("if you meant to pass these as script_args, try "
        "moving them after the --, like this:\n\n")
  u.err("caliban {} -- {} {}\n\n".format(' '.join(before_pre_dashes), joined,
                                         expected_s))
  u.err("Otherwise, if these are in fact caliban keyword arguments, "
        "please move them before the python script/module name argument.\n\n")
  sys.exit(1)


def add_script_args(parser):
  """Adds an argument group that, paired with the validation above, slurps up all
  arguments provided after a '--'.

  """
  parser.add_argument_group("pass-through arguments").add_argument(
      "script_args",
      nargs=REMAINDER,
      default=[],
      metavar="-- YOUR_ARGS",
      help=
      """This is a catch-all for arguments you want to pass through to your script.
any arguments after '--' will pass through.""")


def require_module(parser):
  parser.add_argument(
      "module",
      type=ua.validated_package,
      help=
      "Code to execute, in either trainer.train' or 'trainer/train.py' format. "
      "Accepts python scripts, modules or a path to an arbitrary script.")


def setup_extras(parser):
  parser.add_argument("--extras",
                      action="append",
                      help="setup.py dependency keys.")


def no_cache_arg(parser):
  parser.add_argument("--no_cache",
                      help="Disable Docker's caching mechanism and force"
                      "a rebuild of the container from scratch.",
                      action="store_true")


def docker_run_arg(parser):
  """Adds a command that accepts arguments to pass directly to `docker run`."""
  parser.add_argument("--docker_run_args",
                      type=lambda s: s.split(),
                      help="String of args to add to Docker.")


def extra_dirs(parser):
  parser.add_argument(
      "-d",
      "--dir",
      action="append",
      type=ua.argparse_schema(us.Directory),
      help="Extra directories to include. List these from large to small "
      "to take full advantage of Docker's build cache.")


def no_gpu_flag(parser):
  parser.add_argument("--nogpu",
                      dest="use_gpu",
                      help="Disable GPU mode and force CPU-only.",
                      action="store_false")


def project_id_arg(parser):
  parser.add_argument(
      "--project_id",
      help="ID of the GCloud AI Platform/GKE project to use for Cloud job "
      "submission and image persistence. (Defaults to $PROJECT_ID; errors if "
      "both the argument and $PROJECT_ID are empty.)")


def region_arg(parser):
  regions = u.enum_vals(ct.valid_regions())
  parser.add_argument(
      "--region",
      type=ct.parse_region,
      help="Region to use for Cloud job submission and image persistence. " +
      "Must be one of {}. ".format(regions) +
      "(Defaults to $REGION or '{}'.)".format(conf.DEFAULT_REGION.value))


def cloud_key_arg(parser):
  parser.add_argument("--cloud_key",
                      type=ua.argparse_schema(us.File),
                      help="Path to GCloud service account key. "
                      "(Defaults to $GOOGLE_APPLICATION_CREDENTIALS.)")


def image_id_arg(parser):
  parser.add_argument(
      "--image_id",
      help="Docker image ID accessible in the local Docker registry. "
      "If supplied, Caliban will skip the 'docker build' step and use this image."
  )


def image_tag_arg(parser):
  parser.add_argument(
      "--image_tag",
      help="Docker image tag accessible via Container Registry. If supplied, "
      "Caliban will skip the build and push steps and use this image tag.")


def machine_type_arg(parser):
  machine_types = u.enum_vals(ct.MachineType)
  cpu_default = conf.DEFAULT_MACHINE_TYPE[conf.JobMode.CPU].value
  gpu_default = conf.DEFAULT_MACHINE_TYPE[conf.JobMode.GPU].value

  parser.add_argument("--machine_type",
                      type=ct.parse_machine_type,
                      help="Cloud machine type to request. Must be one of " +
                      "{}. Defaults to '{}' in GPU mode, or '{}' ".format(
                          machine_types, gpu_default, cpu_default) +
                      "if --nogpu is passed.")


# Parsers for each command supported by Caliban.


def base_parser(base):
  "Configures options that every command needs."
  no_gpu_flag(base)
  cloud_key_arg(base)
  setup_extras(base)
  no_cache_arg(base)


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
  experiment_config_arg(base)
  dry_run_arg(base)


def shell_parser(base):
  """Configure the Shell subparser."""
  parser = base.add_parser(
      "shell", help="Start an interactive shell with this dir mounted.")
  base_parser(parser)
  image_id_arg(parser)
  docker_run_arg(parser)
  parser.add_argument(
      "--shell",
      choices=b.Shell,
      type=b.Shell,
      help=
      """This argument sets the shell used inside the container to one of Caliban's
supported shells. Defaults to the shell specified by the $SHELL environment
variable, or 'bash' if your shell isn't supported.""")
  parser.add_argument(
      "--bare",
      action="store_true",
      help="Skip mounting the $HOME directory; load a bare shell.")


def notebook_parser(base):
  """Configure the notebook subparser."""
  parser = base.add_parser("notebook",
                           help="Run a local Jupyter notebook instance.")
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
                      help="Jupyter or Jupyterlab version to install via pip.")
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
      "build",
      help="Build a Docker image without submitting or running any code.")
  building_parser(parser)


def local_run_parser(base):
  """Configure the subparser for `caliban run`."""
  parser = base.add_parser("run", help="Run a job inside a Docker container.")
  executing_parser(parser)
  image_id_arg(parser)
  docker_run_arg(parser)
  xgroup_submit_arg(parser)


def gpu_spec_arg(parser, validate_count: bool = False):
  parser.add_argument(
      "--gpu_spec",
      metavar=ct.GPUSpec.METAVAR,
      type=lambda x: ct.GPUSpec.parse_arg(x, validate_count=validate_count),
      help="Type and number of GPUs to use for each AI Platform/GKE " +
      "submission.  Defaults to 1x{} in GPU mode ".format(
          conf.DEFAULT_GPU.name) + "or None if --nogpu is passed.")


def tpu_spec_arg(parser, validate_count: bool = True):
  parser.add_argument(
      "--tpu_spec",
      metavar=ct.TPUSpec.METAVAR,
      type=lambda x: ct.TPUSpec.parse_arg(x, validate_count=validate_count),
      help="Type and number of TPUs to request for each "
      "AI Platform/GKE submission. Defaults to None.")


def force_arg(parser):
  parser.add_argument(
      "--force",
      action="store_true",
      help="Force past validations and submit the job as specified.")


def job_name_arg(parser):
  parser.add_argument("--name",
                      help="Set a job name for AI Platform or GKE jobs.")


def experiment_config_arg(parser):
  parser.add_argument(
      "--experiment_config",
      type=ce.load_experiment_config,
      help="Path to an experiment config, or 'stdin' to read from stdin.")


def label_arg(parser):
  parser.add_argument("-l",
                      "--label",
                      metavar="KEY=VALUE",
                      action="append",
                      type=ua.parse_kv_pair,
                      help="Extra label k=v pair to submit to Cloud.")


def dry_run_arg(parser):
  parser.add_argument(
      conf.DRY_RUN_FLAG,
      action="store_true",
      help="Don't actually submit; log everything that's going to happen.")


def container_parser(parser):
  executing_parser(parser)

  image_tag_arg(parser)
  project_id_arg(parser)
  region_arg(parser)
  machine_type_arg(parser)
  gpu_spec_arg(parser)
  tpu_spec_arg(parser)
  force_arg(parser)
  job_name_arg(parser)
  label_arg(parser)
  xgroup_submit_arg(parser)


def cloud_parser(base):
  parser = base.add_parser("cloud", help="Submit AI platform jobs to Cloud.")
  container_parser(parser)
  return


def caliban_parser():
  """Creates and returns the argparse instance for the entire Caliban app."""

  parser = argparse_flags.ArgumentParser(description="""Docker and AI
  Platform model training and development script. For detailed
  documentation, visit https://github.com/google/caliban""",
                                         prog="caliban")
  parser.add_argument('--version',
                      action='version',
                      version="%(prog)s {}".format(__version__))

  subparser = parser.add_subparsers(dest="command")
  subparser.required = True

  shell_parser(subparser)
  notebook_parser(subparser)
  local_build_parser(subparser)
  local_run_parser(subparser)
  cloud_parser(subparser)
  cluster_parser(subparser)
  status_parser(subparser)
  stop_parser(subparser)
  resubmit_parser(subparser)

  return parser


# Validations that require access to multiple arguments at once.


def mac_gpu_check(job_mode: conf.JobMode, command: str) -> None:
  """If the command depends on 'docker run' and is running on a Mac, fail fast."""
  if conf.gpu(job_mode) and command in ("shell", "notebook", "run"):
    u.err("\n'caliban {}' doesn't support GPU usage on Macs! Please pass ".
          format(command) + "--nogpu to use this command.\n\n")
    u.err(
        "(GPU mode is fine for 'caliban cloud' from a Mac; just nothing that runs "
        "locally.)\n\n")
    sys.exit(1)


def _validate_no_gpu_type(use_gpu: bool, gpu_spec: Optional[ct.GPUSpec]):
  """Prevents a user from submitting a Cloud job using a CPU image when they've
  explicitly attempted to set a GPU spec.

  """
  gpu_disabled = not use_gpu
  if gpu_disabled and gpu_spec is not None:
    u.err("\n'--nogpu' is incompatible with an explicit --gpu_spec option. "
          "Please remove one or the other!\n\n")
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
      u.err(f"\n'{machine_type.value}' isn't a valid machine type " +
            f"for {gpu_spec.count} {gpu_spec.gpu.name} GPUs.\n\n")
      u.err(ct.with_advice_suffix("gpu", f"Try one of these: {allowed}"))
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
      u.err("\n'{}' isn't a valid region ".format(region.value) +
            "for {}s of type {}.\n\n".format(accel, spec.name))
      u.err("Try one of these: {}\n\n".format(allowed))
      u.err("See this page for more info about regional " +
            "support for {}s: https://cloud.google.com/ml-engine/docs/regions\n"
            .format(accel))
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
  """Function required by absl.app.run.

  Internally generates a parser and returns
  the results of parsing caliban arguments.

  """
  args = argv[1:]
  ret = caliban_parser().parse_args(args)

  # Validate that extra script args were properly parsed.
  validate_script_args(args, vars(ret).get("script_args", []))

  return validate_across_args(ret)


def generate_docker_args(job_mode: conf.JobMode,
                         args: Dict[str, Any]) -> Dict[str, Any]:
  """gemerate docker args from args and job mode"""

  # Get extra dependencies in case you want to install your requirements via a
  # setup.py file.
  setup_extras = b.base_extras(job_mode, "setup.py", args.get("extras"))

  # Google application credentials, from the CLI or from an env variable.
  creds_path = conf.extract_cloud_key(args)

  # Application default credentials location.
  adc_loc = csdk.get_application_default_credentials_path()
  adc_path = adc_loc if os.path.isfile(adc_loc) else None

  # TODO we may want to take custom paths, here, in addition to detecting them.
  reqs = "requirements.txt"
  conda_env = "environment.yml"

  # Arguments that make their way down to caliban.docker.build.build_image.
  docker_args = {
      "extra_dirs": args.get("dir"),
      "requirements_path": reqs if os.path.exists(reqs) else None,
      "conda_env_path": conda_env if os.path.exists(conda_env) else None,
      "caliban_config": conf.caliban_config(),
      "credentials_path": creds_path,
      "adc_path": adc_path,
      "setup_extras": setup_extras,
      "no_cache": args.get("no_cache", False),
      'build_path': os.getcwd(),
  }

  return docker_args


# ----------------------------------------------------------------------------
def cluster_parser(base):
  """cli parser for cluster commands"""

  parser = base.add_parser("cluster",
                           description="cluster commands",
                           help="cluster-related commands")

  subparser = parser.add_subparsers(dest="cluster_cmd")
  cluster_ls_cmd(subparser)
  cluster_pod_parser(subparser)
  cluster_job_parser(subparser)
  cluster_node_pool_parser(subparser)
  cluster_create_cmd(subparser)
  cluster_delete_cmd(subparser)


# ----------------------------------------------------------------------------
def cluster_ls_cmd(base):
  """caliban cluster ls"""

  parser = base.add_parser(
      "ls",
      description="list clusters",
      help="list clusters",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  project_id_arg(parser)
  cloud_key_arg(parser)
  zone_arg(parser)


# ----------------------------------------------------------------------------
def cluster_name_arg(parser):
  parser.add_argument("--cluster_name", help="cluster name", type=str)


# ----------------------------------------------------------------------------
def zone_arg(parser, default=None, help='zone'):
  parser.add_argument("--zone", help=help, type=str, default=default)


# ----------------------------------------------------------------------------
def cluster_pod_parser(base):
  parser = base.add_parser(
      "pod",
      description="pod commands",
      help="pod commands",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  subparser = parser.add_subparsers(dest="pod_cmd")
  cluster_pod_ls_cmd(subparser)


# ----------------------------------------------------------------------------
def cluster_pod_ls_cmd(base):
  parser = base.add_parser("ls", description="list pods", help="list pods")
  project_id_arg(parser)
  cloud_key_arg(parser)
  cluster_name_arg(parser)
  zone_arg(parser)


# ----------------------------------------------------------------------------
def cluster_job_parser(base):
  parser = base.add_parser(
      "job",
      description="job commands",
      help="job commands",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  subparser = parser.add_subparsers(dest="job_cmd")
  cluster_job_ls_cmd(subparser)
  cluster_job_submit_cmd(subparser)
  cluster_job_submit_file_cmd(subparser)


# ----------------------------------------------------------------------------
def cluster_job_ls_cmd(base):
  parser = base.add_parser(
      "ls",
      description="list jobs",
      help="list jobs",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  project_id_arg(parser)
  cloud_key_arg(parser)
  cluster_name_arg(parser)
  zone_arg(parser)


# ----------------------------------------------------------------------------
def cluster_job_submit_cmd(base):
  parser = base.add_parser(
      "submit",
      description="submit cluster job(s)",
      help="submit cluster job(s)",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  cluster_name_arg(parser)
  no_gpu_flag(parser)
  cloud_key_arg(parser)
  setup_extras(parser)
  extra_dirs(parser)
  image_tag_arg(parser)
  project_id_arg(parser)
  min_cpu_arg(parser)
  min_mem_arg(parser)
  gpu_spec_arg(parser, validate_count=False)
  tpu_spec_arg(parser, validate_count=False)
  tpu_driver_arg(parser)
  nonpreemptible_tpu_arg(parser)
  force_arg(parser)
  job_name_arg(parser)
  experiment_config_arg(parser)
  label_arg(parser)
  nonpreemptible_arg(parser)
  dry_run_arg(parser)
  job_export_arg(parser)
  xgroup_submit_arg(parser)

  require_module(parser)
  add_script_args(parser)


# ----------------------------------------------------------------------------
def job_file_arg(parser):
  parser.add_argument('job_file',
                      type=gke_u.validate_job_filename,
                      help='kubernetes k8s job file {}'.format(
                          gke_k.VALID_JOB_FILE_EXT))


# ----------------------------------------------------------------------------
def job_export_arg(parser):
  parser.add_argument(
      '--export',
      type=gke_u.validate_job_filename,
      help=('Export job spec(s) to file, extension must be one of ' +
            '{} (for example: --export my-job-spec.yaml) '.format(
                gke_k.VALID_JOB_FILE_EXT) +
            'For multiple jobs (i.e. in an experiment config scenario), ' +
            'multiple files will be generated with an index inserted ' +
            '(for example: --export my-job-spec.yaml would yield ' +
            'my-job-spec_0.yaml, my-job-spec_1.yaml...)'))


# ----------------------------------------------------------------------------
def cluster_job_submit_file_cmd(base):
  parser = base.add_parser(
      "submit_file",
      description='submit gke job from yaml/json file',
      help='submit gke job from yaml/json file',
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  cluster_name_arg(parser)
  cloud_key_arg(parser)
  project_id_arg(parser)
  dry_run_arg(parser)
  job_file_arg(parser)


# ----------------------------------------------------------------------------
def tpu_driver_arg(parser):
  parser.add_argument("--tpu_driver",
                      type=str,
                      help="tpu driver",
                      default=gke.constants.DEFAULT_TPU_DRIVER)


# ----------------------------------------------------------------------------
def nonpreemptible_tpu_arg(parser):
  parser.add_argument(
      "--nonpreemptible_tpu",
      action="store_true",
      help=("use non-preemptible tpus: "
            "note this only applies to v2-8 and v3-8 tpus currently, see: "
            "https://cloud.google.com/tpu/docs/preemptible"))


# ----------------------------------------------------------------------------
def nonpreemptible_arg(parser):
  parser.add_argument(
      "--nonpreemptible",
      action="store_true",
      help=
      ("use non-preemptible VM instance: "
       "please note that you may need to upgrade your "
       "cluster to a recent version/use the rapid release "
       "channel for preemptible VMs to be supported with node autoprovisioning: "
       "https://cloud.google.com/kubernetes-engine/docs/release-notes-rapid#december_13_2019"
      ))


# ----------------------------------------------------------------------------
def cluster_node_pool_parser(base):
  parser = base.add_parser(
      "node_pool",
      description="node pool commands",
      help="node pool commands",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  subparser = parser.add_subparsers(dest="node_pool_cmd")
  cluster_node_pool_ls_cmd(subparser)


# ----------------------------------------------------------------------------
def cluster_node_pool_ls_cmd(base):
  parser = base.add_parser(
      "ls",
      description="list node pools",
      help="list node pools",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)
  project_id_arg(parser)
  cloud_key_arg(parser)
  cluster_name_arg(parser)
  zone_arg(parser)


# ----------------------------------------------------------------------------
def cluster_create_cmd(base):
  """caliban cluster create"""

  parser = base.add_parser(
      "create",
      description="create cluster",
      help="create cluster",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  project_id_arg(parser)
  cloud_key_arg(parser)
  cluster_name_arg(parser)
  zone_arg(
      parser,
      help='for a single-zone cluster, this specifies the zone '
      'for the cluster control plane and all worker nodes, while for a '
      'multi-zone cluster this specifies only the zone for the control plane, '
      'while worker nodes may be created in any zone within the same region as '
      'the control plane. The single_zone argument specifies whether to create '
      'a single- or multi- zone cluster.')
  dry_run_arg(parser)
  release_channel_arg(parser)
  single_zone_arg(parser)


# ----------------------------------------------------------------------------
def cluster_delete_cmd(base):
  """caliban cluster delete"""

  parser = base.add_parser(
      "delete",
      description="delete cluster",
      help="delete cluster",
      formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  project_id_arg(parser)
  cloud_key_arg(parser)
  cluster_name_arg(parser)
  zone_arg(parser)


# ----------------------------------------------------------------------------
def release_channel_arg(parser):
  parser.add_argument(
      "--release_channel",
      metavar=[x.value for x in gke_t.ReleaseChannel],
      choices=gke_t.ReleaseChannel,
      type=gke_t.ReleaseChannel,
      help="cluster release channel, see "
      "https://cloud.google.com/kubernetes-engine/docs/concepts/release-channels",
      default=gke.constants.DEFAULT_RELEASE_CHANNEL.value)


# ----------------------------------------------------------------------------
def single_zone_arg(parser):
  parser.add_argument(
      "--single_zone",
      action="store_true",
      help=
      ('create a single-zone cluster if set, otherwise create a multi-zone '
       'cluster: see https://cloud.google.com/kubernetes-engine/docs/concepts/'
       'types-of-clusters#cluster_availability_choices'))


# ----------------------------------------------------------------------------
def min_cpu_arg(parser):
  parser.add_argument(
      '--min_cpu',
      type=int,
      help='Minimum cpu needed by job, in milli-cpus. If not specified, then '
      'this value defaults to {} for gpu/tpu jobs, and {} for cpu jobs. Please '
      'note that gke daemon processes utilize a small amount of cpu on each node, '
      'so if you want to have your job run on a specific machine type, say a 2-cpu '
      'machine, then if you specify a minimum cpu of 2000, then your job will '
      'not be schedulable on a 2-cpu machine as the daemon processes will push '
      'the total cpu needed to more than two full cpus.'.format(
          gke_k.DEFAULT_MIN_CPU_ACCEL, gke_k.DEFAULT_MIN_CPU_CPU))


# ----------------------------------------------------------------------------
def min_mem_arg(parser):
  parser.add_argument(
      '--min_mem',
      type=int,
      help='Minimum memory needed by job, in MB. Please note that gke '
      'daemon processes utilize a small amount of memory on each node, so if '
      'you want to have your job run on a specific machine type, say a machine '
      'with 8GB total memory, then if you specify a minimum memory of 8000MB, '
      'then your job will not be schedulable on a 8GB machine as the daemon '
      'processes will push the total memory needed to more than 8GB.')


# ----------------------------------------------------------------------------
def xgroup_arg(parser, helpstr: str):
  parser.add_argument(
      '--xgroup',
      type=str,
      help=helpstr,
  )


def xgroup_submit_arg(parser):
  xgroup_arg(
      parser,
      helpstr=
      f'This specifies an experiment group, which ties experiments and job '
      f'instances together. If you do not specify a group, then a new one will be '
      f'created. If you specify an existing experiment group here, then new '
      f'experiments and jobs you create will be added to the group you specify.',
  )


# ----------------------------------------------------------------------------
def status_parser(base):
  '''cli parser for status command'''

  parser = base.add_parser("status", help="get status for caliban jobs")
  xgroup_arg(parser, helpstr='experiment group')
  max_jobs_arg(parser)


# ----------------------------------------------------------------------------
def stop_parser(base):
  '''cli parser for stop command'''
  parser = base.add_parser('stop', help='stop running caliban jobs')
  xgroup_arg(parser, helpstr='experiment group')
  dry_run_arg(parser)


# ----------------------------------------------------------------------------
def all_jobs_arg(parser):
  parser.add_argument(
      '--all_jobs',
      action='store_true',
      help=(f'resubmit all jobs regardless of current state, otherwise only '
            f'jobs that are in FAILED or STOPPED state will be resubmitted'))


# ----------------------------------------------------------------------------
def resubmit_parser(base):
  '''cli parser for resubmit command'''
  parser = base.add_parser('resubmit', help='resubmit caliban jobs')
  xgroup_arg(parser, helpstr='experiment group')
  dry_run_arg(parser)
  all_jobs_arg(parser)
  project_id_arg(parser)
  cloud_key_arg(parser)


# ----------------------------------------------------------------------------
def max_jobs_arg(parser):
  parser.add_argument(
      '--max_jobs',
      type=int,
      help=(f'Maximum number of jobs to view. If you specify an experiment '
            f'group, then this specifies the maximum number of jobs per '
            f'experiment to view. If you do not specify an experiment group, '
            f'then this specifies the total number of jobs to return, ordered '
            f'by creation date, or all jobs if max_jobs==0.'),
  )
