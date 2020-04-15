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
