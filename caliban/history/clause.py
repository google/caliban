'''base clause'''

import operator
from typing import Dict, Any, Optional
from caliban.history.interfaces import QueryOp


# ----------------------------------------------------------------------------
class Clause(object):
  '''a clause in a query

  field: field for comparison, in dot-path format
  op: operation to apply
  value: value for comparison against field
  '''

  _OP = {
      QueryOp.LT: operator.lt,
      QueryOp.LE: operator.le,
      QueryOp.GT: operator.gt,
      QueryOp.GE: operator.ge,
      QueryOp.EQ: operator.eq,
      QueryOp.IN: lambda a, b: operator.contains(b, a)
  }

  def __init__(self, field: str, op: QueryOp, value: Any):
    self.field = field
    self.op = op
    self.value = value

  def _get_field(self, d: Dict[str, Any]) -> Optional[Any]:
    '''gets value for given field

    Args:
    d: dictionary from which to get value

    Returns:
    value for given field, or None on error
    '''
    for k in self.field.split('.'):
      d = d.get(k)
      if d is None:
        return
    return d

  def __call__(self, d: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    '''applies clause filter to dictionary

    Args:
    d: dictionary to test

    Returns:
    input dictionary if clause is true, None otherwise
    '''
    try:
      f = self._get_field(d)
      if f is None:
        return None
      return d if self._OP[self.op](f, self.value) else None
    except Exception as e:
      print(e)
      return None

  def __str__(self) -> str:
    return '{} {} {}'.format(self.field, self.op.value, self.value)
