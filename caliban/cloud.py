"""Cloud utilities."""

from __future__ import absolute_import, division, print_function

import datetime
import subprocess
from typing import Dict, List, Optional

from absl import logging
from googleapiclient import discovery, errors

import caliban.docker as d
import caliban.util as u

US_REGIONS = ["us-west1", "us-west2", "us-central1", "us-east1", "us-east4"]
EURO_REGIONS = ["europe-west1", "europe-west4", "europe-north1"]
ASIA_REGIONS = ["asia-southeast1", "asia-east1", "asia-northeast1"]
DEFAULT_REGION = "us-central1"


def valid_regions(zone: Optional[str] = None) -> List[str]:
  """Returns valid region strings for Cloud, for the globe or for a particular
  region if specified.

  """
  if zone is None:
    return US_REGIONS + EURO_REGIONS + ASIA_REGIONS

  z = zone.lower()

  if "americas" == z:
    return US_REGIONS
  elif "europe" == z:
    return EURO_REGIONS
  elif "asia" == z:
    return ASIA_REGIONS
  else:
    raise ValueError(
        f"invalid zone: {zone}. Must be one of 'americas', 'europe', 'asia'.")


def job_url(project_id: str, job_id: str) -> str:
  """Returns a URL that will load the default page for the newly launched cloud
  job.

  """
  prefix = "https://pantheon.corp.google.com/ai-platform/jobs"
  return f"{prefix}/{job_id}?projectId={project_id}"


def _stream_cmd(job_id: str) -> List[str]:
  return ["gcloud", "ai-platform", "jobs", "stream-logs", job_id]


def stream_ml_logs(job_id: str) -> None:
  """
  TODO this should validate whether or not the job actually exists.
  """
  subprocess.call(_stream_cmd(job_id))


def create_ml_job(job_spec, parent):
  """This submits the actual job."""

  #cache_discovery=False prevents an error bubbling up from a missing file
  #cache, which no user of this code is going to be using.
  ml = discovery.build('ml', 'v1', cache_discovery=False)
  request = ml.projects().jobs().create(body=job_spec, parent=parent)

  try:
    response = request.execute()
    logging.info("Request succeeded!")
    logging.info("Response:")
    logging.info(response)
    return response

  except errors.HttpError as err:
    logging.error("There was an error submitting the job. Check the details:")
    logging.error(err._get_reason())


def submit_package(use_gpu: bool,
                   package: u.Package,
                   region: str,
                   project_id: str,
                   stream_logs: bool = True,
                   script_args: Optional[List[str]] = None,
                   job_name: Optional[str] = None,
                   labels: Optional[Dict[str, str]] = None,
                   **kwargs) -> None:
  """Submit a container to the cloud.

  Cloud API docs for the endpoint we use here:
  https://cloud.google.com/ml-engine/reference/rest/v1/projects.jobs/create

  Use this when we configure hyper-parameter sweeps to run lots of experiments:
  https://cloud.google.com/ml-engine/reference/rest/v1/projects.jobs#hyperparameterspec

  kwargs are extra arguments to d._dockerfile_template.
  """
  if script_args is None:
    script_args = []

  custom_name = True

  if job_name is None:
    custom_name = False
    job_name = "default_name"

  if labels is None:
    labels = {}

  # TODO make this configurable. BUT bake in knowledge from the links below
  # about what regions actually support GPU usage.
  master_type = "standard_p100" if use_gpu else "complex_model_l"

  timestamp = datetime.datetime.now().strftime('_%Y_%m_%d_%H_%M_%S')
  job_id = f"{job_name}_{timestamp}"

  logging.info(f"Running remote job with GPU: {use_gpu} and package: \
{package}, args: {script_args}")

  image_id = d.build_image(use_gpu, package=package, **kwargs)
  image_tag = d.push_uuid_tag(project_id, image_id)

  training_input = {
      # https://cloud.google.com/ml-engine/reference/rest/v1/projects.jobs#ReplicaConfig
      #
      # Also the GPU compatibility table. This is important for when we upgrade
      # from the legacy machine definition.
      # https://cloud.google.com/ml-engine/docs/using-gpus#gpu-compatibility-table
      #
      # This is also where we can do some work if we do want to support TPUs.
      "masterConfig": {
          "imageUri": image_tag
      },
      "scaleTier": "CUSTOM",
      "masterType": master_type,
      "args": script_args,
      "region": region
  }

  cloud_labels = {"gpu_enabled": str(use_gpu).lower()}

  if custom_name:
    # Don't supply a job_name label if we're using the default name.
    cloud_labels.update({"job_name": job_name})

  cloud_labels.update(u.script_args_to_labels(script_args))
  cloud_labels.update(labels)

  job_spec = {
      "jobId": job_id,
      "trainingInput": training_input,
      "labels": cloud_labels
  }

  # Store the full project ID in a variable in the format the API needs.
  parent = f"projects/{project_id}"

  logging.debug(f"Submitting job with job spec: {job_spec}")
  logging.debug(f"parent: {parent}")

  create_ml_job(job_spec, parent)

  logging.info(f"Job submission successful for job ID {job_id}")
  stream_command = " ".join(_stream_cmd(job_id))
  url = job_url(project_id, job_id)

  if stream_logs:
    logging.info(f"""Streaming logs for {job_id}.

Feel free to kill this process. You can always resume streaming by running:

{stream_command}

(Also note that the log streamer will NOT exit when the job completes!)

Visit the following page to see info on your job:

{url}
""")
    stream_ml_logs(job_id)
  else:
    logging.info(f"""You can stream the logs with the following command:

{stream_command}

Visit the following page to see info on your job:

{url}
""")
