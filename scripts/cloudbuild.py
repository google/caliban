#!/usr/bin/env python
'''creates cloudbuild.json for caliban'''

from absl import flags, app, logging
from typing import Dict, List, Any, NamedTuple, Optional
from enum import Enum

import json
import pprint as pp

# ----------------------------------------------------------------------------
_CLOUD_BUILDER = 'gcr.io/cloud-builders/docker'
_BASE_URL = 'gcr.io/blueshift-playground/blueshift'
_GPU_BASE_TAG = 'base'
_CPU_TAG = 'cpu'
_GPU_TAG = 'gpu'
_CPU_BASE_IMAGE = 'ubuntu:18.04'
_CPU_DOCKERFILE = 'dockerfiles/Dockerfile'
_GPU_DOCKERFILE = 'dockerfiles/Dockerfile.gpu'

# ----------------------------------------------------------------------------
FLAGS = flags.FLAGS

flags.DEFINE_string('output', None, 'output json file')
flags.DEFINE_string('config', None, 'input configuration file')
flags.DEFINE_string('base_url', _BASE_URL, 'base url for images')
flags.DEFINE_integer('timeout_sec', 24 * 60 * 60,
                     'timeout for all builds to complete')

# ----------------------------------------------------------------------------
logging.get_absl_handler().setFormatter(None)

Config = Dict[str, Any]


# ----------------------------------------------------------------------------
class BuildStep(NamedTuple):
  '''a google cloud-build step'''
  step_id: str
  name: str = _CLOUD_BUILDER
  args: List[str] = []
  dependencies: List[str] = ['-']

  def to_dict(self) -> Dict[str, Any]:
    return {
        'id': self.step_id,
        'name': self.name,
        'args': self.args,
        'waitFor': self.dependencies,
    }


# ----------------------------------------------------------------------------
class ImageType(Enum):
  GPU_BASE = 'GPU_BASE'
  CPU = 'CPU'
  GPU = 'GPU'


class ImageSpec(NamedTuple):
  '''a caliban base image spec'''
  dockerfile: str = _CPU_DOCKERFILE
  base_image: Optional[str] = _CPU_BASE_IMAGE
  cpu_version: Optional[str] = None
  gpu_version: Optional[str] = None
  build_args: List[str] = []

  @property
  def image_type(self) -> ImageType:
    if self.gpu_version is None:
      return ImageType.CPU
    else:
      if self.cpu_version is None:
        return ImageType.GPU_BASE
      else:
        return ImageType.GPU

  @property
  def tag(self) -> str:
    parts = []
    if self.image_type == ImageType.CPU:
      parts = [_CPU_TAG, self.cpu_version]
    else:
      parts.append(_GPU_TAG)
      if self.image_type == ImageType.GPU_BASE:
        parts += ['base', self.gpu_version]
      else:
        parts += [self.gpu_version, self.cpu_version]

    return f'{FLAGS.base_url}:' + '-'.join(parts)


# ----------------------------------------------------------------------------
def _create_push_step(tag: str) -> BuildStep:
  return BuildStep(step_id=f'{tag}-push',
                   args=['push', tag],
                   dependencies=[tag])


# ----------------------------------------------------------------------------
def _create_gpu_base_image_specs(cfg: Config) -> Dict[str, ImageSpec]:
  return {
      k: ImageSpec(base_image=None,
                   gpu_version=k,
                   build_args=v,
                   dockerfile=_GPU_DOCKERFILE) for k, v in cfg.items()
  }


# ----------------------------------------------------------------------------
def _create_cpu_image_specs(cfg: Config) -> Dict[str, ImageSpec]:
  return {k: ImageSpec(cpu_version=k, build_args=v) for k, v in cfg.items()}


# ----------------------------------------------------------------------------
def _create_image_spec(
    cfg: Config,
    cpu_specs: Dict[str, ImageSpec],
    gpu_specs: Dict[str, ImageSpec],
) -> ImageSpec:
  gpu_version = cfg.get('gpu')
  cpu_spec = cpu_specs[cfg.get('python')]

  if gpu_version is None:
    return cpu_spec

  return ImageSpec(base_image=gpu_specs[gpu_version].tag,
                   cpu_version=cpu_spec.cpu_version,
                   gpu_version=gpu_version,
                   build_args=cpu_spec.build_args)


# ----------------------------------------------------------------------------
def _create_specs(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
  conda_cfg = cfg['python_versions']
  cuda_cfg = cfg['gpu_versions']

  gpu_specs = _create_gpu_base_image_specs(cfg.get('gpu_versions', {}))
  cpu_specs = _create_cpu_image_specs(cfg.get('python_versions', {}))

  specs = list(gpu_specs.values())
  specs += [
      _create_image_spec(cfg=c, cpu_specs=cpu_specs, gpu_specs=gpu_specs)
      for c in cfg.get('images', [])
  ]

  return specs


# ----------------------------------------------------------------------------
def _create_build_step(spec: ImageSpec) -> BuildStep:
  args = ['build']
  args += ['-t', spec.tag]
  args += ['-f', spec.dockerfile]

  if spec.base_image is not None:
    args.append('--build-arg')
    args.append(f'BASE_IMAGE={spec.base_image}')

  for a in spec.build_args:
    args.append('--build-arg')
    args.append(a)
  args.append('.')

  if spec.image_type == ImageType.GPU:
    dependencies = [spec.base_image]
  else:
    dependencies = ['-']

  return BuildStep(step_id=spec.tag, args=args, dependencies=dependencies)


# ----------------------------------------------------------------------------
def main(argv):
  with open(FLAGS.config, 'r') as f:
    config = json.load(f)

  specs = _create_specs(cfg=config)

  steps = []
  for s in specs:
    steps.append(_create_build_step(spec=s).to_dict())
    steps.append(_create_push_step(tag=s.tag).to_dict())

  with open(FLAGS.output, 'w') as f:
    json.dump({'steps': steps, 'timeout': f'{FLAGS.timeout_sec}s'}, f, indent=2)


# ----------------------------------------------------------------------------
if __name__ == '__main__':
  app.run(main)
