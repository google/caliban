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

import json
from argparse import ArgumentTypeError

import caliban.config.experiment as c
import caliban.util as u
import caliban.util.schema as us
import pytest


def test_validate_experiment_config():
  """basic examples of validate experiment config."""
  invalid = {1: "face", "2": "3"}
  with pytest.raises(ArgumentTypeError):
    c.validate_experiment_config(invalid)

  # a dict value is invalid, even if it's hidden in a list.
  with pytest.raises(ArgumentTypeError):
    c.validate_experiment_config({"key": [{1: 2}, "face"]})

  valid = {"a": [1.0, 2, 3], "b": True, "c": 1, "d": "e", "f": 1.2}
  assert valid == c.validate_experiment_config(valid)

  # Lists are okay too...
  items = [valid, valid]
  assert items == c.validate_experiment_config(items)

  # As are lists of lists.
  lol = [valid, [valid]]
  assert lol == c.validate_experiment_config(lol)

  # Invalid types are caught even nested inside lists.
  lol_invalid = [valid, valid, [invalid]]

  with pytest.raises(ArgumentTypeError):
    c.validate_experiment_config(lol_invalid)

  # Compound keys which violate syntax rules are caught
  invalid_compound = [{
      "[": 0
  }, {
      "eh[": 0
  }, {
      "[test,,fail]": 0
  }, {
      "[,test,fail]": 0
  }, {
      "[I,will,fail,]": 0
  }, {
      "[I,,will,fail]": 0
  }, {
      "]I,will,fail]": 0
  }]

  valid_compound = [{
      "[batch_size,learning_rate]": [0, 1]
  }, {
      "[batch_size,learning_rate,dataset_size]": [0.01, 0.02, 100]
  }, {
      "[batch_size,learning_rate,dataset_size]": [[0.01, 0.02, 100],
                                                  [0.03, 0.05, 200]]
  }, {
      "[batch_size,learning_rate]": [[0., 1.], [2., 3.]]
  }, {
      "[batch_size,learning_rate]": [[0., 1.], [2., 3.], [4., 5.]]
  }, {
      "[batch_size, learning_rate, dataset_size]": [0.01, 0.02, 100]
  }, {
      "[batch_size , learning_rate,dataset_size]": [[0.01, 0.02, 100],
                                                    [0.03, 0.05, 200]]
  }, {
      "[batch_size, learning_rate]": [[0., 1.], [2., 3.]]
  }, {
      "[batch_size ,learning_rate]": [[0., 1.], [2., 3.], [4., 5.]]
  }]

  for i in invalid_compound:
    with pytest.raises(Exception):
      c.validate_experiment_config(i)

  for i in valid_compound:
    assert i == c.validate_experiment_config(i)


def test_expand_experiment_config():
  # An empty config expands to a singleton list. This is important so that
  # single job submission without a spec works.
  assert [{}] == c.expand_experiment_config({})


def test_compound_key_handling():
  """tests the full assembly line transforming a configuration dictionary
    including compound keys into a list of dictionaries for passing to the
    script

  """
  tests = [{
      'input': {
          '[a,b]': [['c', 'd'], ['e', 'f']]
      },
      'after_tupleization': {
          ('a', 'b'): [('c', 'd'), ('e', 'f')]
      },
      'after_dictproduct': [{
          ('a', 'b'): ('c', 'd')
      }, {
          ('a', 'b'): ('e', 'f')
      }],
      'after_expansion': [{
          'a': 'c',
          'b': 'd'
      }, {
          'a': 'e',
          'b': 'f'
      }]
  }, {
      'input': {
          '[a,b]': ['c', 'd']
      },
      'after_tupleization': {
          ('a', 'b'): ('c', 'd')
      },
      'after_dictproduct': [{
          ('a', 'b'): ('c', 'd')
      }],
      'after_expansion': [{
          'a': 'c',
          'b': 'd'
      }]
  }, {
      'input': {
          'hi': 'there',
          '[k1,k2]': [['v1a', 'v2a'], ['v1b', 'v2b']]
      },
      'after_tupleization': {
          'hi': 'there',
          ('k1', 'k2'): [('v1a', 'v2a'), ('v1b', 'v2b')]
      },
      'after_dictproduct': [{
          'hi': 'there',
          ('k1', 'k2'): ('v1a', 'v2a')
      }, {
          'hi': 'there',
          ('k1', 'k2'): ('v1b', 'v2b')
      }],
      'after_expansion': [{
          'hi': 'there',
          'k1': 'v1a',
          'k2': 'v2a'
      }, {
          'hi': 'there',
          'k1': 'v1b',
          'k2': 'v2b'
      }]
  }, {
      'input': {
          'hi': 'there',
          '[a,b]': ['c', 'd']
      },
      'after_tupleization': {
          'hi': 'there',
          ('a', 'b'): ('c', 'd')
      },
      'after_dictproduct': [{
          'hi': 'there',
          ('a', 'b'): ('c', 'd')
      }],
      'after_expansion': [{
          'hi': 'there',
          'a': 'c',
          'b': 'd'
      }]
  }, {
      'input': {
          '[a,b]': [0, 1]
      },
      'after_tupleization': {
          ('a', 'b'): (0, 1)
      },
      'after_dictproduct': [{
          ('a', 'b'): (0, 1)
      }],
      'after_expansion': [{
          'a': 0,
          'b': 1
      }]
  }, {
      'input': {
          '[a,b]': [[0, 1]]
      },
      'after_tupleization': {
          ('a', 'b'): [(0, 1)]
      },
      'after_dictproduct': [{
          ('a', 'b'): (0, 1)
      }],
      'after_expansion': [{
          'a': 0,
          'b': 1
      }]
  }, {
      'input': {
          'hi': 'blueshift',
          '[a,b]': [[0, 1]]
      },
      'after_tupleization': {
          'hi': 'blueshift',
          ('a', 'b'): [(0, 1)]
      },
      'after_dictproduct': [{
          'hi': 'blueshift',
          ('a', 'b'): (0, 1)
      }],
      'after_expansion': [{
          'hi': 'blueshift',
          'a': 0,
          'b': 1
      }]
  }]

  for test in tests:
    assert test['after_tupleization'] == c.tupleize_dict(test['input'])
    assert test['after_expansion'] == list(
        c.expand_compound_dict(test['after_dictproduct']))
    assert test['after_expansion'] == c.expand_experiment_config(test['input'])
    assert test['after_dictproduct'] == list(
        u.dict_product(test['after_tupleization']))


def test_load_experiment_config(tmpdir):
  valid = {"key": ['a', 'b'], "random": [True, False]}
  valid_path = tmpdir.join('valid.json')

  with open(valid_path, 'w') as f:
    json.dump(valid, f)

  invalid_path = tmpdir.join('invalid.json')

  with open(invalid_path, 'w') as f:
    f.write("{{{I am not JSON!\n")

  # Failing the schema with invalid json raises an ARGPARSE error, not a schema
  # error. We haven't converted experimentconfig to schema yet.
  #
  # We use schema to validate, but the ua.argparse_schema wrapper converts the
  # error internally.
  with pytest.raises(ArgumentTypeError):
    c.load_experiment_config(invalid_path)

  # A valid config should round trip.
  assert c.load_experiment_config(valid_path) == valid
