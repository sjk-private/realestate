import string

def GetInt(s):
  """Treats the provided string as an integer and parses it.

  :param s:
  :return:
  """
  try:
    return int(filter(lambda x: x in string.digits, s))
  except Exception:
    return 1

def SafeDivide(x, y, default=1.0):
  try:
    return '%.02f' % (float(x) / float(y))
  except Exception:
    return default

class BaseBunch(object):
  """A simple container for named fields/values.
  """
  def __init__(self, from_dict=None, **kwargs):
    self.__dict__.update(kwargs)
    if from_dict:
      self.__dict__.update(from_dict)

  def __eq__(self, other):
    return isinstance(other, BaseBunch) and (self.__dict__ == other.__dict__)

  def __ne__(self, other):
    return not self.__eq__(other)

  def __repr__(self):
    import pprint
    return '%s(%s)' % (self.__class__.__name__, pprint.pformat(self.__dict__))

  def __getitem__(self, obj):
    return self.__dict__[obj]

  def __iter__(self):
    return self.__dict__.iterkeys()

  def __contains__(self, key):
    return key in self.__dict__

  def __nonzero__(self):
    return len(self.__dict__) > 0

  def __len__(self):
    return len(self.__dict__)

  def keys(self):
    return self.__dict__.keys()

  def values(self):
    return self.__dict__.values()

  def get(self, attr, default=None):
    return self.__dict__.get(attr, default)

  def items(self):
    return self.__dict__.items()

  def iterkeys(self):
    return self.__dict__.iterkeys()

  def itervalues(self):
    return self.__dict__.itervalues()

  def iteritems(self):
    return self.__dict__.iteritems()

  def ToDict(self):
    """Returns the fields and values as a copy of the underlying
    dict structure.
    """
    return dict(self.__dict__)

class ImmutableBunch(BaseBunch):
  """An immutable BaseBunch that is NOT hashable.
  """
  # Disallow any further modification of this structure.
  __setattr__ = None
  __delattr__ = None
  __setitem__ = None
  __delitem__ = None
  __hash__ = None

class FrozenBunch(ImmutableBunch):
  """An ImmutableBunch that IS hashable.
  """
  def __init__(self, from_dict=None, **kwargs):
    super(FrozenBunch, self).__init__(from_dict=from_dict, **kwargs)
    self.__dict__['_hash'] = hash(frozenset(kwargs.iteritems()))

  def __hash__(self):
    return self._hash

class Bunch(BaseBunch):
  """A mutable BaseBunch. Should not be hashable since it's mutable.
  """
  def __setitem__(self, obj, val):
    self.__dict__[obj] = val

  def __delitem__(self, obj):
    del self.__dict__[obj]
