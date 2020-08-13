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
"""unit tests for gke utilities"""
import random
import unittest
from typing import List, Optional, Dict
from unittest import mock
import uuid
import json
import os
import tempfile
import yaml

import hypothesis.strategies as st
from hypothesis import given, settings
from kubernetes.client.api_client import ApiClient
from kubernetes.client import V1Job
import pytest
import argparse
import google

import caliban.platform.cloud.types as ct
import caliban.platform.gke.constants as k
import caliban.platform.gke.util as util
from caliban.platform.gke.types import NodeImage, OpStatus
from caliban.platform.gke.util import trap


# ----------------------------------------------------------------------------
def everything():
  """hypothesis utility to generate, well, everything"""
  return st.from_type(type).flatmap(st.from_type)


# ----------------------------------------------------------------------------
def everything_except(excluded_types):
  """hypothesis utility to generate everything but the types in excluded_types"""
  return everything().filter(lambda x: not isinstance(x, tuple(excluded_types)))


# ----------------------------------------------------------------------------
class UtilTestSuite(unittest.TestCase):
  """tests for caliban.platform.gke.util"""

  # --------------------------------------------------------------------------
  @given(
      st.lists(st.integers(min_value=0, max_value=4),
               min_size=len(ct.GPU),
               max_size=len(ct.GPU)), st.sampled_from(ct.GPU),
      st.integers(min_value=1, max_value=8))
  def test_validate_gpu_spec_against_limits(
      self,
      limits: List[int],
      gpu_type: ct.GPU,
      count: int,
  ):
    """tests gpu validation against limits"""

    gpu_list = [g for g in ct.GPU]
    gpu_limits = dict([
        (gpu_list[i], limits[i]) for i in range(len(limits)) if limits[i]
    ])
    spec = ct.GPUSpec(gpu_type, count)
    valid = util.validate_gpu_spec_against_limits(spec, gpu_limits, 'test')

    if spec.gpu not in gpu_limits:
      self.assertFalse(valid)
    else:
      self.assertTrue(valid == (spec.count <= gpu_limits[spec.gpu]))

    return

  # --------------------------------------------------------------------------
  def test_validate_gpu_spec_against_limits_deterministic(self):
    '''deterministic test to make sure we get full coverage'''

    # gpu not supported
    cfg = {
        'gpu_spec': ct.GPUSpec(ct.GPU.K80, 1),
        'gpu_limits': {
            ct.GPU.P100: 1
        },
        'limit_type': 'zone',
    }
    assert not util.validate_gpu_spec_against_limits(**cfg)

    # request above limit
    cfg = {
        'gpu_spec': ct.GPUSpec(ct.GPU.K80, 2),
        'gpu_limits': {
            ct.GPU.P100: 1,
            ct.GPU.K80: 1,
        },
        'limit_type': 'zone',
    }
    assert not util.validate_gpu_spec_against_limits(**cfg)

    # valid request
    cfg = {
        'gpu_spec': ct.GPUSpec(ct.GPU.K80, 1),
        'gpu_limits': {
            ct.GPU.P100: 1,
            ct.GPU.K80: 1,
        },
        'limit_type': 'zone',
    }
    assert util.validate_gpu_spec_against_limits(**cfg)

  # --------------------------------------------------------------------------
  def test_nvidia_daemonset_url(self):
    """tests nvidia driver daemonset url generation"""
    VALID_NODE_IMAGES = [NodeImage.COS, NodeImage.UBUNTU]

    for n in NodeImage:
      url = util.nvidia_daemonset_url(n)

      if n in VALID_NODE_IMAGES:
        self.assertIsNotNone(url)
      else:
        self.assertIsNone(url)

    return

  # --------------------------------------------------------------------------
  @mock.patch('caliban.platform.gke.util.input', create=True)
  @given(st.lists(st.from_regex('^[^yYnN]+$'), min_size=0, max_size=8))
  def test_user_verify(
      self,
      mocked_input,
      invalid_strings,
  ):
    """tests user verify method"""

    # verify different defaults
    for default in [True, False]:

      # default input
      mocked_input.side_effect = ['']
      self.assertEqual(util.user_verify('test default', default=default),
                       default)

      # upper/lower true input
      for x in ['y', 'Y']:
        mocked_input.side_effect = invalid_strings + [x]
        self.assertTrue(util.user_verify('y input', default=default))

      # upper/lower false input
      for x in ['n', 'N']:
        mocked_input.side_effect = invalid_strings + [x]
        self.assertFalse(util.user_verify('n input', default=default))

    return

  # --------------------------------------------------------------------------
  @given(everything())
  def test_trap(self, return_val):
    """tests trap decorator"""

    def _raises():
      raise Exception('exception!')

    # make sure the test function works..testing the tester
    with self.assertRaises(Exception) as e:
      _raises()

    valid_return = '42'

    def _no_raise():
      return valid_return

    # ibid
    self.assertEqual(valid_return, _no_raise())

    print('testing return_val = {}'.format(return_val))

    @trap(return_val)
    def _test_raises():
      _raises()

    @trap(return_val)
    def _test_no_raise():
      return _no_raise()

    # test for types where we can't test equality
    try:
      if return_val != return_val:
        return
    except:
      return

    if valid_return == return_val:
      return

    self.assertEqual(return_val, _test_raises())
    self.assertEqual(valid_return, _test_no_raise())

    return

  # --------------------------------------------------------------------------
  @given(
      st.lists(st.sampled_from(list(OpStatus)), min_size=1, max_size=8),
      st.sets(st.sampled_from(list(OpStatus)),
              min_size=1,
              max_size=len(OpStatus)),
      st.sets(st.from_regex('\A_[a-zA-Z0-9]+\Z'), min_size=1, max_size=4),
  )
  @settings(deadline=1000)  # in ms
  def test_wait_for_operation(self, results, conds, invalid_cond):
    """tests wait_for_operation method"""

    class mock_api:

      def projects(self):
        return self

      def locations(self):
        return self

      def operations(self):
        return self

      def get(self, name):
        return self

    def _raises():
      raise Exception('exception')

    def _return_results():
      for r in results:
        yield {'status': r.value}
      _raises()

    api = mock_api()
    api.execute = _raises

    # we run without the wait spinner here as it causes the tests
    # to take about a factor of 100 longer

    # empty condition list
    self.assertIsNone(util.wait_for_operation(api, 'name', [], spinner=False))

    # exception
    self.assertIsNone(
        util.wait_for_operation(api, 'name', list(conds), 0, spinner=False))

    # normal operation
    rsp_generator = _return_results()
    api.execute = lambda: next(rsp_generator)

    expected_response = None
    for r in results:
      if r in conds:
        expected_response = r.value
        break

    if expected_response is not None:
      self.assertEqual({'status': expected_response},
                       util.wait_for_operation(api,
                                               'name',
                                               list(conds),
                                               0,
                                               spinner=True))
    else:
      self.assertIsNone(
          util.wait_for_operation(api, 'name', list(conds), 0, spinner=False))

    return

  # --------------------------------------------------------------------------
  @given(
      st.sets(
          st.tuples(st.integers(min_value=1, max_value=32),
                    st.sampled_from(ct.TPU))),
      st.sets(st.from_regex('\A_[a-z0-9]+-[0-9]+\Z')),
  )
  def test_get_zone_tpu_types(self, tpu_types, invalid_types):
    """tests get_zone_tpu_types"""

    tpus = ['{}-{}'.format(x[1].name.lower(), x[0]) for x in tpu_types]

    invalid_types = list(invalid_types)

    responses = tpus + invalid_types
    random.shuffle(responses)

    class mock_api:

      def projects(self):
        return self

      def locations(self):
        return self

      def acceleratorTypes(self):
        return self

      def list(self, parent):
        return self

    def _raises():
      raise Exception('exception')

    def _response():
      return {'acceleratorTypes': [{'type': x} for x in responses]}

    def _invalid_response():
      return {'foo': 'bar'}

    api = mock_api()

    # exception handling
    api.execute = _raises
    self.assertIsNone(util.get_zone_tpu_types(api, 'p', 'z'))

    # invalid response
    api.execute = _invalid_response
    self.assertIsNone(util.get_zone_tpu_types(api, 'p', 'z'))

    # normal mode
    api.execute = _response
    self.assertEqual(
        sorted(tpus),
        sorted([
            '{}-{}'.format(x.name.lower(), x.count)
            for x in util.get_zone_tpu_types(api, 'p', 'z')
        ]))

    return

  # --------------------------------------------------------------------------
  @given(st.text())
  def test_sanitize_job_name(self, job_name):
    """test job name sanitizer"""

    def valid(x):
      return k.DNS_1123_RE.match(x) is not None

    sanitized = util.sanitize_job_name(job_name)

    if valid(job_name):
      self.assertEqual(job_name, sanitized)
    else:
      self.assertTrue(valid(sanitized))

    # idempotency check
    self.assertEqual(sanitized, util.sanitize_job_name(sanitized))

    # ensure coverage, first char must be alnum, last must be alnum
    x = '_' + sanitized + '-'
    assert valid(util.sanitize_job_name(x))

    return

  # --------------------------------------------------------------------------
  @given(
      st.lists(st.integers(min_value=0, max_value=32),
               min_size=len(ct.GPU),
               max_size=len(ct.GPU)),
      st.sets(
          st.tuples(st.from_regex('\A[a-z0-9]+\Z'),
                    st.integers(min_value=1, max_value=32))),
  )
  def test_get_zone_gpu_types(self, gpu_counts, invalid_types):
    """tests get_zone_gpu_types"""

    gpu_types = ['nvidia-tesla-{}'.format(x.name.lower()) for x in ct.GPU]

    gpus = [{
        'name': gpu_types[i],
        'maximumCardsPerInstance': c
    } for i, c in enumerate(gpu_counts) if c > 0]

    invalid = [{
        'name': x[0],
        'maximumCardsPerInstance': x[1]
    } for x in invalid_types]

    class mock_api:

      def acceleratorTypes(self):
        return self

      def list(self, project, zone):
        return self

    def _raises():
      raise Exception('exception')

    def _response():
      return {'items': gpus + invalid}

    def _invalid_response():
      return {'foo': 'bar'}

    api = mock_api()

    # exception handling
    api.execute = _raises
    self.assertIsNone(util.get_zone_gpu_types(api, 'p', 'z'))

    # invalid response
    api.execute = _invalid_response
    self.assertIsNone(util.get_zone_gpu_types(api, 'p', 'z'))

    # normal execution
    api.execute = _response
    self.assertEqual(
        sorted([
            '{}-{}'.format(x["name"], x["maximumCardsPerInstance"])
            for x in gpus
        ]),
        sorted([
            'nvidia-tesla-{}-{}'.format(x.gpu.name.lower(), x.count)
            for x in util.get_zone_gpu_types(api, 'p', 'z')
        ]))

    return

  # --------------------------------------------------------------------------
  def test_get_region_quotas(self):
    """tests get region quotas"""

    class mock_api:

      def regions(self):
        return self

      def get(self, project, region):
        return self

    def _raises():
      raise Exception('exception')

    def _normal():
      return {
          'quotas': [{
              'limit': 4,
              'metric': 'CPUS',
              'usage': 1
          }, {
              'limit': 1024,
              'metric': 'NVIDIA_K80_GPUS',
              'usage': 0
          }]
      }

    def _invalid():
      return {'foo': 'bar'}

    api = mock_api()

    # exception handling
    api.execute = _raises
    self.assertIsNone(util.get_region_quotas(api, 'p', 'r'))

    # invalid return
    api.execute = _invalid
    self.assertEqual([], util.get_region_quotas(api, 'p', 'r'))

    # normal execution
    api.execute = _normal
    self.assertEqual(_normal()['quotas'], util.get_region_quotas(api, 'p', 'r'))

    return

  # --------------------------------------------------------------------------
  def test_generate_resource_limits(self):
    """tests generation of resource limits"""

    class mock_api:

      def regions(self):
        return self

      def get(self, project, region):
        return self

    def _raises():
      raise Exception('exception')

    def _normal():
      return {
          'quotas': [{
              'limit': 4,
              'metric': 'CPUS',
              'usage': 1
          }, {
              'limit': 1024,
              'metric': 'NVIDIA_K80_GPUS',
              'usage': 0
          }]
      }

    def _invalid():
      return {'foo': 'bar'}

    api = mock_api()

    # exception handling
    api.execute = _raises
    self.assertIsNone(util.generate_resource_limits(api, 'p', 'r'))

    # invalid return
    api.execute = _invalid
    self.assertEqual([], util.generate_resource_limits(api, 'p', 'r'))

    # normal execution
    api.execute = _normal
    quotas = _normal()['quotas']
    expected = ([{
        'resourceType': 'cpu',
        'maximum': str(quotas[0]['limit'])
    }] + [{
        'resourceType': 'memory',
        'maximum': str(quotas[0]['limit'] * k.MAX_GB_PER_CPU)
    }] + [{
        'resourceType': 'nvidia-tesla-k80',
        'maximum': str(quotas[1]['limit'])
    }])

    self.assertEqual(expected, util.generate_resource_limits(api, 'p', 'r'))

    return

  # --------------------------------------------------------------------------
  @given(st.lists(st.from_regex('[a-zA-Z0-9]+')),
         st.from_regex('_[a-zA-Z0-9]+'))
  def test_get_gke_cluster(self, names, invalid):
    """test getting gke cluster"""

    class mock_cluster:

      def __init__(self, name):
        self.name = name
        return

    class mock_cluster_list:

      def __init__(self):
        self.clusters = [mock_cluster(x) for x in names]
        return

    class mock_api:
      self.throws = False

      def list_clusters(self, project_id, zone):
        if self.throws:
          raise Exception('exception')
        return mock_cluster_list()

    api = mock_api()
    api.throws = True

    # exception handling
    self.assertIsNone(util.get_gke_cluster(api, 'foo', 'p'))

    api.throws = False
    # single cluster
    if len(names) > 0:
      cname = names[random.randint(0, len(names) - 1)]
      self.assertEqual(cname, util.get_gke_cluster(api, cname, 'p').name)

    # name not in name list
    self.assertIsNone(util.get_gke_cluster(api, invalid, 'p'))

    return

  # --------------------------------------------------------------------------
  def _validate_nonnull_dict(self, d: dict, ref: dict):
    """helper method for testing nonnull_dict, nonnull_list"""
    for k, v in d.items():
      self.assertIsNotNone(v)
      self.assertTrue(k in ref)
      self.assertEqual(type(v), type(ref[k]))
      if trap(True)(lambda z: z != z)(v):
        continue
      elif type(v) == dict:
        self._validate_nonnull_dict(v, ref[k])
      elif type(v) == list:
        self._validate_nonnull_list(v, ref[k])
      else:
        self.assertEqual(v, ref[k])

  # --------------------------------------------------------------------------
  def _validate_nonnull_list(self, lst: list, ref: list):
    """helper method for testing nonnull_dict, nonnull_list"""
    ref = [x for x in ref if x is not None]
    self.assertEqual(len(lst), len(ref))
    for i, x in enumerate(lst):
      self.assertIsNotNone(x)
      self.assertEqual(type(x), type(ref[i]))
      if trap(True)(lambda z: z != z)(x):
        continue
      elif type(x) == list:
        self._validate_nonnull_list(x, ref[i])
      elif type(x) == dict:
        self._validate_nonnull_dict(x, ref[i])
      else:
        self.assertEqual(x, ref[i])

  # --------------------------------------------------------------------------
  @given(st.dictionaries(
      keys=st.from_regex('\A[a-z]+\Z'),
      values=everything(),
  ))
  def test_nonnull_dict(self, input_dict):
    input_dict[str(uuid.uuid1())] = {'x': None, 'y': 7}  # ensure coverage
    input_dict[str(uuid.uuid1())] = [1, 2, None, 3]
    self._validate_nonnull_dict(util.nonnull_dict(input_dict), input_dict)
    return

  # --------------------------------------------------------------------------
  @given(st.lists(everything()))
  def test_nonnull_list(self, input_list):
    input_list.append({'x': None, 'y': 7})  # ensure coverage
    input_list.append([1, 2, None, 3])  # ensure coverage
    self._validate_nonnull_list(util.nonnull_list(input_list), input_list)
    return

  # --------------------------------------------------------------------------
  @given(
      st.sampled_from(
          list(set.union(ct.US_REGIONS, ct.EURO_REGIONS, ct.ASIA_REGIONS))),
      st.sets(st.from_regex('\A[a-z]\Z')))
  def test_get_zones_in_region(self, region, zone_ids):
    '''test get_zones_in_region'''

    class mock_api:

      def regions(self):
        return self

      def get(self, project, region):
        return self

    def _raises():
      raise Exception('exception')

    url = 'https://www.googleapis.com/compute/v1/projects/foo/zones/'
    zones = ['{}-{}'.format(region, x) for x in zone_ids]

    def _normal():
      return {'zones': ['{}{}'.format(url, x) for x in zones]}

    def _invalid():
      return {'foo': 'bar'}

    api = mock_api()

    # exception handling
    api.execute = _raises
    self.assertIsNone(util.get_zones_in_region(api, 'p', region))

    # invalid return
    api.execute = _invalid
    self.assertIsNone(util.get_zones_in_region(api, 'p', region))

    # normal execution
    api.execute = _normal
    self.assertEqual(zones, util.get_zones_in_region(api, 'p', region))


# ----------------------------------------------------------------------------
def test_dashboard_cluster_url():
  cfg = {
      'cluster_id': 'foo',
      'zone': 'us-central1-a',
      'project_id': 'bar',
  }

  url = util.dashboard_cluster_url(**cfg)

  assert url is not None
  assert url == (f'{k.DASHBOARD_CLUSTER_URL}/{cfg["zone"]}/{cfg["cluster_id"]}'
                 f'?project={cfg["project_id"]}')


# ----------------------------------------------------------------------------
def test_get_tpu_drivers(monkeypatch):

  class MockApi():

    def __init__(self,
                 drivers: Optional[Dict[str, Dict[str, List[str]]]] = None):
      self._drivers = drivers

    def projects(self):
      return self

    def locations(self):
      return self

    def tensorflowVersions(self):
      return self

    def list(self, parent):
      return self

    def execute(self):
      return self._drivers

  # test no response behavior
  cfg = {'tpu_api': MockApi(), 'project_id': 'foo', 'zone': 'us-central1-a'}

  assert util.get_tpu_drivers(**cfg) is None

  # test valid response
  drivers = ['foo', 'bar']
  cfg['tpu_api'] = MockApi(
      drivers={'tensorflowVersions': [{
          'version': x
      } for x in drivers]})

  assert util.get_tpu_drivers(**cfg) == drivers


# ----------------------------------------------------------------------------
def test_resource_limits_from_quotas():

  # valid, all quota > 0
  counts = {'cpu': 1, 'nvidia-tesla-p100': 2, 'memory': k.MAX_GB_PER_CPU}
  quotas = [('CPUS', counts['cpu']),
            ('NVIDIA_P100_GPUS', counts['nvidia-tesla-p100']), ('bogus', 5)]
  cfg = {'quotas': [{'metric': x[0], 'limit': x[1]} for x in quotas]}

  q = util.resource_limits_from_quotas(**cfg)
  assert len(q) == len(counts)
  for d in q:
    assert counts[d['resourceType']] == int(d['maximum'])

  # valid, gpu quota == 0
  counts = {'cpu': 1, 'nvidia-tesla-p100': 0, 'memory': k.MAX_GB_PER_CPU}
  quotas = [('CPUS', counts['cpu']),
            ('NVIDIA_P100_GPUS', counts['nvidia-tesla-p100'])]
  cfg = {'quotas': [{'metric': x[0], 'limit': x[1]} for x in quotas]}

  q = util.resource_limits_from_quotas(**cfg)
  assert len(q) == len(counts) - 1
  for d in q:
    assert d['resourceType'] != 'nvidia-tesla-p100'
    assert counts[d['resourceType']] == int(d['maximum'])


# ----------------------------------------------------------------------------
def test_job_to_dict():
  j = V1Job(api_version='abc', kind='foo')
  d = util.job_to_dict(j)

  assert d is not None
  assert isinstance(d, dict)
  assert d == ApiClient().sanitize_for_serialization(j)


# ----------------------------------------------------------------------------
def test_job_str():
  j = V1Job(api_version='abc', kind='foo')
  s = util.job_str(j)
  assert s is not None
  assert isinstance(s, str)


# ----------------------------------------------------------------------------
def test_validate_job_filename():
  for x in k.VALID_JOB_FILE_EXT:
    fname = str(uuid.uuid1()) + f'.{x}'
    s = util.validate_job_filename(fname)
    assert s == fname

  with pytest.raises(argparse.ArgumentTypeError):
    fname = str(uuid.uuid1()) + '.' + str(uuid.uuid1())
    util.validate_job_filename(fname)


# ----------------------------------------------------------------------------
def test_export_job():
  with tempfile.TemporaryDirectory() as tmpdir:

    j = V1Job(api_version='abc', kind='foo')
    nnd = util.nonnull_dict(util.job_to_dict(j))

    fname = os.path.join(tmpdir, 'foo.json')
    assert util.export_job(j, fname)
    assert os.path.exists(fname)
    with open(fname, 'r') as f:
      x = json.load(f)
    assert x == nnd

    fname = os.path.join(tmpdir, 'foo.yaml')
    assert util.export_job(j, fname)
    assert os.path.exists(fname)
    with open(fname, 'r') as f:
      x = yaml.load(f)
    assert x == nnd

    fname = os.path.join(tmpdir, 'foo.xyz')
    assert not util.export_job(j, fname)


# ----------------------------------------------------------------------------
def test_application_default_credentials_path(monkeypatch):
  adc = 'foo'
  # monkeypatch can't set things in underscore-prefixed modules, so we
  # cheat a bit here
  monkeypatch.setattr(util, 'get_application_default_credentials_path',
                      lambda: adc)
  assert util.application_default_credentials_path() == adc


# ----------------------------------------------------------------------------
def test_default_credentials(monkeypatch):

  class MockCreds():

    def refresh(self, req):
      pass

  creds = MockCreds()
  project_id = 'project-foo'

  def mock_default(scopes):
    return (creds, project_id)

  monkeypatch.setattr(google.auth, 'default', mock_default)
  monkeypatch.setattr(google.auth.transport.requests, 'Request', lambda: None)

  cd = util.default_credentials()

  assert cd.credentials == creds
  assert cd.project_id == project_id


# ----------------------------------------------------------------------------
def test_credentials_from_file(monkeypatch):

  class MockCreds():

    def refresh(self, req):
      pass

  creds = MockCreds()
  project_id = 'foo-project'

  def mock_from_service_account_file(f, scopes):
    return creds

  def mock_load_credentials_from_file(f):
    return (creds, project_id)

  monkeypatch.setattr(google.auth.transport.requests, 'Request', lambda: None)
  monkeypatch.setattr(google.oauth2.service_account.Credentials,
                      'from_service_account_file',
                      mock_from_service_account_file)

  # ugh, I feel dirty, but monkeypatching google.auth._default.load_credentials_from_file
  # doesn't work
  monkeypatch.setattr(util, 'load_credentials_from_file',
                      mock_load_credentials_from_file)

  # test service account file
  creds_type = util._SERVICE_ACCOUNT_TYPE
  with tempfile.TemporaryDirectory() as tmpdir:
    creds_dict = {'type': creds_type, 'project_id': project_id}

    creds_file = os.path.join(tmpdir, 'creds.json')
    with open(creds_file, 'w') as f:
      json.dump(creds_dict, f)

    cd = util.credentials_from_file(creds_file)
    assert cd.credentials == creds
    assert cd.project_id == project_id

  # test authorized user file
  creds_type = util._AUTHORIZED_USER_TYPE
  with tempfile.TemporaryDirectory() as tmpdir:
    creds_dict = {'type': creds_type, 'project_id': project_id}

    creds_file = os.path.join(tmpdir, 'creds.json')
    with open(creds_file, 'w') as f:
      json.dump(creds_dict, f)

    cd = util.credentials_from_file(creds_file)
    assert cd.credentials == creds
    assert cd.project_id == project_id

  # test invalid file
  creds_type = str(uuid.uuid1())
  with tempfile.TemporaryDirectory() as tmpdir:
    creds_dict = {'type': creds_type, 'project_id': project_id}

    creds_file = os.path.join(tmpdir, 'creds.json')
    with open(creds_file, 'w') as f:
      json.dump(creds_dict, f)

    cd = util.credentials_from_file(creds_file)
    assert cd.credentials is None
    assert cd.project_id is None


# ----------------------------------------------------------------------------
def test_credentials(monkeypatch):

  class MockCreds():

    def refresh(self, req):
      pass

  creds = MockCreds()
  project_id = 'project-foo'

  def mock_default(scopes):
    return (creds, project_id)

  def mock_from_service_account_file(f, scopes):
    return creds

  monkeypatch.setattr(google.auth, 'default', mock_default)
  monkeypatch.setattr(google.auth.transport.requests, 'Request', lambda: None)
  monkeypatch.setattr(google.oauth2.service_account.Credentials,
                      'from_service_account_file',
                      mock_from_service_account_file)

  # test default creds
  cd = util.credentials()
  assert cd.credentials == creds
  assert cd.project_id == project_id

  # test creds file
  creds_type = util._SERVICE_ACCOUNT_TYPE
  with tempfile.TemporaryDirectory() as tmpdir:
    creds_dict = {'type': creds_type, 'project_id': project_id}

    creds_file = os.path.join(tmpdir, 'creds.json')
    with open(creds_file, 'w') as f:
      json.dump(creds_dict, f)

    cd = util.credentials(creds_file)
    assert cd.credentials == creds
    assert cd.project_id == project_id


# ----------------------------------------------------------------------------
def test_parse_job_file():

  # test invalid file extension
  with tempfile.TemporaryDirectory() as tmpdir:
    cfg = {'foo': 1, 'bar': '2'}
    fname = os.path.join(tmpdir, f'job.{str(uuid.uuid1())}')
    with open(fname, 'w') as f:
      json.dump(cfg, f)

    assert os.path.exists(fname)
    d = util.parse_job_file(fname)
    assert d is None

  # test missing file
  d = util.parse_job_file(f'{str(uuid.uuid1())}.json')
  assert d is None

  # test json file
  with tempfile.TemporaryDirectory() as tmpdir:
    cfg = {'foo': 1, 'bar': '2'}
    fname = os.path.join(tmpdir, f'job.json')
    with open(fname, 'w') as f:
      json.dump(cfg, f)

    assert os.path.exists(fname)
    d = util.parse_job_file(fname)
    assert d == cfg

  # test yaml file
  with tempfile.TemporaryDirectory() as tmpdir:
    cfg = {'foo': 1, 'bar': '2'}
    fname = os.path.join(tmpdir, f'job.yaml')
    with open(fname, 'w') as f:
      yaml.dump(cfg, f)

    assert os.path.exists(fname)
    d = util.parse_job_file(fname)
    assert d == cfg

  # test bad formatting
  with tempfile.TemporaryDirectory() as tmpdir:
    fname = os.path.join(tmpdir, f'job.json')
    with open(fname, 'w') as f:
      f.write('this is invalid json')

    assert os.path.exists(fname)
    d = util.parse_job_file(fname)
    assert d is None
