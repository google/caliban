"""unit tests for gke utilities"""
import unittest
from unittest import mock
import random

import hypothesis.strategies as st
from hypothesis import given, settings
from typing import Dict, List, Any
import re
import random

import caliban.cloud.types as ct
import caliban.gke
import caliban.gke.utils as utils
import caliban.gke.constants as k
from caliban.gke.utils import trap, DNS_1123_RE
from caliban.gke.types import NodeImage, OpStatus


# ----------------------------------------------------------------------------
def everything():
  """hypothesis utility to generate, well, everything"""
  return st.from_type(type).flatmap(st.from_type)


# ----------------------------------------------------------------------------
def everything_except(excluded_types):
  """hypothesis utility to generate everything but the types in excluded_types"""
  return everything().filter(lambda x: not isinstance(x, tuple(excluded_types)))


# ----------------------------------------------------------------------------
class UtilsTestSuite(unittest.TestCase):
  """tests for caliban.gke.utils"""

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
    valid = utils.validate_gpu_spec_against_limits(spec, gpu_limits, 'test')

    if spec.gpu not in gpu_limits:
      self.assertFalse(valid)
    else:
      self.assertTrue(valid == (spec.count <= gpu_limits[spec.gpu]))

    return

  # --------------------------------------------------------------------------
  def test_nvidia_daemonset_url(self):
    """tests nvidia driver daemonset url generation"""
    VALID_NODE_IMAGES = [NodeImage.COS, NodeImage.UBUNTU]

    for n in NodeImage:
      url = utils.nvidia_daemonset_url(n)

      if n in VALID_NODE_IMAGES:
        self.assertIsNotNone(url)
      else:
        self.assertIsNone(url)

    return

  # --------------------------------------------------------------------------
  @mock.patch('caliban.gke.utils.input', create=True)
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
      self.assertEqual(utils.user_verify('test default', default=default),
                       default)

      # upper/lower true input
      for x in ['y', 'Y']:
        mocked_input.side_effect = invalid_strings + [x]
        self.assertTrue(utils.user_verify('y input', default=default))

      # upper/lower false input
      for x in ['n', 'N']:
        mocked_input.side_effect = invalid_strings + [x]
        self.assertFalse(utils.user_verify('n input', default=default))

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

    print(f'testing return_val = {return_val}')

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

    # avoid stupid testing errors
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
    self.assertIsNone(utils.wait_for_operation(api, 'name', [], spinner=False))

    # exception
    self.assertIsNone(
        utils.wait_for_operation(api, 'name', list(conds), 0, spinner=False))

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
                       utils.wait_for_operation(api,
                                                'name',
                                                list(conds),
                                                0,
                                                spinner=False))
    else:
      self.assertIsNone(
          utils.wait_for_operation(api, 'name', list(conds), 0, spinner=False))

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

    tpus = [f'{x[1].name.lower()}-{x[0]}' for x in tpu_types]

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
    self.assertIsNone(utils.get_zone_tpu_types(api, 'p', 'z'))

    # invalid response
    api.execute = _invalid_response
    self.assertIsNone(utils.get_zone_tpu_types(api, 'p', 'z'))

    # normal mode
    api.execute = _response
    self.assertEqual(
        sorted(tpus),
        sorted([
            f'{x.name.lower()}-{x.count}'
            for x in utils.get_zone_tpu_types(api, 'p', 'z')
        ]))

    return

  # --------------------------------------------------------------------------
  @given(st.text())
  def test_sanitize_job_name(self, job_name):
    """test job name sanitizer"""

    def valid(x):
      return DNS_1123_RE.match(x) is not None

    sanitized = utils.sanitize_job_name(job_name)

    if valid(job_name):
      self.assertEqual(job_name, sanitized)
    else:
      self.assertTrue(valid(sanitized))

    # idempotency check
    self.assertEqual(sanitized, utils.sanitize_job_name(sanitized))

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

    gpu_types = [f'nvidia-tesla-{x.name.lower()}' for x in ct.GPU]

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
    self.assertIsNone(utils.get_zone_gpu_types('p', 'z', api))

    # invalid response
    api.execute = _invalid_response
    self.assertIsNone(utils.get_zone_gpu_types('p', 'z', api))

    # normal execution
    api.execute = _response
    self.assertEqual(
        sorted([f'{x["name"]}-{x["maximumCardsPerInstance"]}' for x in gpus]),
        sorted([
            f'nvidia-tesla-{x.gpu.name.lower()}-{x.count}'
            for x in utils.get_zone_gpu_types('p', 'z', api)
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
    self.assertIsNone(utils.get_region_quotas('p', 'r', api))

    # invalid return
    api.execute = _invalid
    self.assertEqual([], utils.get_region_quotas('p', 'r', api))

    # normal execution
    api.execute = _normal
    self.assertEqual(_normal()['quotas'],
                     utils.get_region_quotas('p', 'r', api))

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
    self.assertIsNone(utils.generate_resource_limits('p', 'r', api))

    # invalid return
    api.execute = _invalid
    self.assertEqual([], utils.generate_resource_limits('p', 'r', api))

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

    self.assertEqual(expected, utils.generate_resource_limits('p', 'r', api))

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
    self.assertIsNone(utils.get_gke_cluster(api, 'foo', 'p'))

    api.throws = False
    # single cluster
    if len(names) > 0:
      cname = names[random.randint(0, len(names) - 1)]
      self.assertEqual(cname, utils.get_gke_cluster(api, cname, 'p').name)

    # name not in name list
    self.assertIsNone(utils.get_gke_cluster(api, invalid, 'p'))

    return
