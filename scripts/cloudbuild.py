#!/usr/bin/env python
'''creates cloudbuild.json for caliban'''

from absl import flags, app, logging
from copy import copy
from typing import Dict, List, Any, NamedTuple, Optional, Set
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


class GpuBase(NamedTuple):
  base_image: str
  gpu: str

  @property
  def tag(self) -> str:
    return f'{self.base_image}-{self.gpu}'


class CpuBase(NamedTuple):
  base_image: str
  python: str

  @property
  def tag(self) -> str:
    return f'{self.base_image}-{self.python}'


class ImageSpec(NamedTuple):
  '''a caliban base image spec'''
  dockerfile: str = _CPU_DOCKERFILE
  base_image: Optional[str] = _CPU_BASE_IMAGE
  cpu_version: Optional[str] = None
  gpu_version: Optional[str] = None
  build_args: Dict[str, str] = {}

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
      parts = [_CPU_TAG, self.base_image, self.cpu_version]
    else:
      parts.append(_GPU_TAG)
      if self.image_type == ImageType.GPU_BASE:
        parts += ['base', self.base_image, self.gpu_version]
      else:
        parts += [self.base_image, self.cpu_version, self.gpu_version]

    return f'{FLAGS.base_url}:' + '-'.join(parts)


# ----------------------------------------------------------------------------
def _create_push_step(tag: str) -> BuildStep:
  return BuildStep(step_id=f'{tag}-push',
                   args=['push', tag],
                   dependencies=[tag])


# ----------------------------------------------------------------------------
def _get_unique_gpu_bases(images: List[Config]) -> Set[GpuBase]:
  gpu_base_images = set()

  for x in images:
    if x.get('gpu') is None:
      continue
    gpu_base_images.add(GpuBase(base_image=x['base_image'], gpu=x['gpu']))

  return gpu_base_images


# ----------------------------------------------------------------------------
def _create_gpu_base_image_specs(
    images: List[Config],
    base_img_cfg: Config,
    gpu_cfg: Config,
) -> Dict[str, ImageSpec]:
  specs = {}

  for b in _get_unique_gpu_bases(images=images):
    base = base_img_cfg[b.base_image]
    build_args = copy(gpu_cfg[b.gpu])
    build_args['UBUNTU_VERSION'] = base['UBUNTU_VERSION']

    specs[b.tag] = ImageSpec(
        base_image=b.base_image,
        gpu_version=b.gpu,
        build_args=build_args,
        dockerfile=_GPU_DOCKERFILE,
    )

  return specs


# ----------------------------------------------------------------------------
def _get_unique_cpu_bases(images: List[Config]) -> Set[CpuBase]:
  bases = set()
  for x in images:
    if x.get('gpu') is not None:
      continue
    bases.add(CpuBase(base_image=x['base_image'], python=x['python']))

  return bases


# ----------------------------------------------------------------------------
def _create_cpu_image_specs(
    images: List[Config],
    base_img_cfg: Config,
    cpu_cfg: Config,
) -> Dict[str, ImageSpec]:

  specs = {}
  for b in _get_unique_cpu_bases(images):
    base = base_img_cfg[b.base_image]
    build_args = copy(cpu_cfg[b.python])
    build_args['BASE_IMAGE'] = base["BASE_IMAGE"]

    specs[b.tag] = ImageSpec(base_image=b.base_image,
                             cpu_version=b.python,
                             gpu_version=None,
                             build_args=build_args)

  return specs


# ----------------------------------------------------------------------------
def _create_image_spec(
    cfg: Config,
    cpu_specs: Dict[str, ImageSpec],
    gpu_specs: Dict[str, ImageSpec],
) -> ImageSpec:

  cpu_base = CpuBase(base_image=cfg['base_image'], python=cfg['python'])
  cpu_spec = cpu_specs[cpu_base.tag]

  gpu_version = cfg.get('gpu')
  if gpu_version is None:
    return cpu_spec

  gpu_base = GpuBase(base_image=cfg['base_image'], gpu=cfg['gpu'])
  gpu_spec = gpu_specs[gpu_base.tag]

  build_args = copy(cpu_spec.build_args)
  build_args['BASE_IMAGE'] = gpu_spec.tag

  return ImageSpec(base_image=cpu_spec.base_image,
                   cpu_version=cpu_spec.cpu_version,
                   gpu_version=gpu_version,
                   build_args=build_args)


# ----------------------------------------------------------------------------
def _create_specs(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
  gpu_cfg = cfg.get('gpu_versions', {})
  python_cfg = cfg.get('python_versions', {})
  base_img_cfg = cfg.get('base_images', {})
  images = cfg.get('images', [])

  gpu_specs = _create_gpu_base_image_specs(
      images=images,
      base_img_cfg=base_img_cfg,
      gpu_cfg=gpu_cfg,
  )

  cpu_specs = _create_cpu_image_specs(
      images=images,
      base_img_cfg=base_img_cfg,
      cpu_cfg=python_cfg,
  )

  specs = list(gpu_specs.values())  # gpu base images
  specs += [
      _create_image_spec(cfg=c, cpu_specs=cpu_specs, gpu_specs=gpu_specs)
      for c in images
  ]

  return specs


# ----------------------------------------------------------------------------
def _create_build_step(spec: ImageSpec) -> BuildStep:
  args = ['build']
  args += ['-t', spec.tag]
  args += ['-f', spec.dockerfile]

  for k, v in spec.build_args.items():
    args.append('--build-arg')
    args.append(f'{k}={v}')
  args.append('.')

  if spec.image_type == ImageType.GPU:
    dependencies = [spec.build_args['BASE_IMAGE']]
  else:
    dependencies = ['-']

  return BuildStep(step_id=spec.tag, args=args, dependencies=dependencies)


# ----------------------------------------------------------------------------
def main(argv):
  with open(FLAGS.config, 'r') as f:
    config = json.load(f)

  specs = _create_specs(cfg=config)

  print(f'generating the following images in {FLAGS.output}:')
  for s in specs:
    print(f'{s.tag}')

  steps = []
  for s in specs:
    steps.append(_create_build_step(spec=s).to_dict())
    steps.append(_create_push_step(tag=s.tag).to_dict())

  with open(FLAGS.output, 'w') as f:
    json.dump({'steps': steps, 'timeout': f'{FLAGS.timeout_sec}s'}, f, indent=2)


# ----------------------------------------------------------------------------
if __name__ == '__main__':
  app.run(main)
