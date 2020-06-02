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
'''general caliban types'''

from typing import Union, Optional, TypeVar, Generic, Any, Type, NewType


class Ignored():
  '''ignored'''


Ignore = Ignored()
''' This is a simple TypeVar that is useful when you want to use
 typing.Optional, but None is a valid type that you need to handle.
 For example:
 def foo(x: Union[Optional[str], Ignored] = Ignore):
   if x == Ignore:
     print('ignored')
   else:
     print(x)

 foo()
 foo(None)
 foo('bar')

 returns:
   ignored
   None
   bar

Note that mypy sometimes will not be able to handle the above conditional,
so you may have to use isinstance(x, Ignored) instead of (x == Ignore).
'''
