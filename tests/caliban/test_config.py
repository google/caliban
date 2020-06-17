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

import os
import unittest
from argparse import ArgumentTypeError

import caliban.cloud.types as ct
import caliban.config as c
import pytest


def test_extract_region(monkeypatch):
  if os.environ.get('REGION'):
    monkeypatch.delenv('REGION')

  assert c.extract_region({}) == c.DEFAULT_REGION

  # You have to provide a valid region.
  with pytest.raises(ArgumentTypeError):
    c.extract_region({"region": "face"})

  # Same goes for the environment variable setting approach.
  monkeypatch.setenv('REGION', "face")
  with pytest.raises(ArgumentTypeError):
    c.extract_region({})

  # an empty string is fine, and ignored.
  monkeypatch.setenv('REGION', "")
  assert c.extract_region({}) == c.DEFAULT_REGION

  assert c.extract_region({"region": "us-west1"}) == ct.US.west1


class ConfigTestSuite(unittest.TestCase):
  """Tests for the config package."""

  def test_validate_experiment_config(self):
    """basic examples of validate experiment config."""
    invalid = {1: "face", "2": "3"}
    with self.assertRaises(ArgumentTypeError):
      c.validate_experiment_config(invalid)

    # a dict value is invalid, even if it's hidden in a list.
    with self.assertRaises(ArgumentTypeError):
      c.validate_experiment_config({"key": [{1: 2}, "face"]})

    valid = {"a": [1.0, 2, 3], "b": True, "c": 1, "d": "e", "f": 1.2}
    self.assertDictEqual(valid, c.validate_experiment_config(valid))

    # Lists are okay too...
    items = [valid, valid]
    self.assertListEqual(items, c.validate_experiment_config(items))

    # As are lists of lists.
    lol = [valid, [valid]]
    self.assertListEqual(lol, c.validate_experiment_config(lol))

    # Invalid types are caught even nested inside lists.
    lol_invalid = [valid, valid, [invalid]]
    with self.assertRaises(ArgumentTypeError):
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
      with self.assertRaises(Exception):
        c.validate_experiment_config(i)
    for i in valid_compound:
      self.assertDictEqual(i, c.validate_experiment_config(i))

  def test_expand_experiment_config(self):
    # An empty config expands to a singleton list. This is important so that
    # single job submission without a spec works.
    self.assertListEqual([{}], c.expand_experiment_config({}))

  def test_compound_key_handling(self):
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
      self.assertListEqual(test['after_expansion'],
                           c.expand_experiment_config(test['input']))


if __name__ == '__main__':
  unittest.main()
