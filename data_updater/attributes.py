"""Data model for the attributes of a property.
"""

from misc_util import GetInt, SafeDivide
import re

class PropertyAttribute(object):

  def __init__(self, name, rank):
    self.name = name
    self.rank = rank

  def Render(self):
    return self.name

  def __repr__(self):
    return self.name


class PropertyAttributeWithValue(object):
  def __init__(self, property_attribute, value):
    self.property_attribute = property_attribute
    self.value = value

  def Render(self):
    return self.value

  def __repr__(self):
    return '%s: %s' % (self.property_attribute.name, self.value)

class PropertyAttributes(object):
  """Container for set of property attributes.
  """

  def __init__(self, attrs):
    self.attr_name_to_attr = dict((a.property_attribute.name, a) for a in attrs)

  def Merge(self, attrs_other):
    for a in attrs_other.attr_name_to_attr.values():
      self.attr_name_to_attr[a.property_attribute.name] = a

  def __repr__(self):
    return '%s' % self.attr_name_to_attr.values()

  def RenderToSpreadsheet(self, cells):
    """Return the attributes in the form of spreadsheet cells.

    :return:
    """
    for c in cells.values():
      c.value = ''

    for i, a in enumerate(ATTRIBUTES_RANKED):
      cells[i].value = self.GetValue(a.name)

    return cells

  def GetValue(self, attr_name):
    return self.attr_name_to_attr[attr_name].value

class FactParser(object):

  def __init__(self, name, regex, rank):
    self.name = name
    self.regex = re.compile(regex)
    self.rank = rank

  def Parse(self, fact_string):
    """Parse out from the provided fact string.
    """
    match = self.regex.match(fact_string)
    if match:
      return match.group(1)

class DerivedAttribute(object):

  def __init__(self, name, rank, attrs, fn):
    self.name = name
    self.rank = rank
    self.attrs = attrs
    self.fn = fn

  def Apply(self):
    """Applies the function to the static attributes.
    """
    return 'blah'

ALL_FACT_PARSERS = [
  FactParser('built_year', 'Built in\s+(.*)', 103),
  FactParser('lot_size', 'Lot:\s+(.*)\s+sqft', 102),
  FactParser('days_on_zillow', '(.*)\s+days on Zillow', 110),
  FactParser('views', 'Views:\s+([0-9,]+)', 111),
  FactParser('saved', '(.*) shoppers saved', 112),
  FactParser('price_sqft_zillow', 'Price/sqft:\s+\$(\d+)', 1101),
  FactParser('mls', 'MLS.*(\d+)', 200),
  FactParser('parking', 'Parking: (.*)', 113),
  FactParser('stories', 'Stories: (\d+)', 114),
  FactParser('floor_size', 'Floor size:\s+([0-9,])\s+sqft', 104),
  FactParser('cooling', 'Cooling:\s+(.*)', 105),
  FactParser('heating', 'Heating:\s+(.*)', 106),
  FactParser('last_remodel', 'Last remodel year: (\d+)', 115),
  FactParser('room_count', 'Room count: (\d+)', 116),
  FactParser('last_sold', 'Last sold: (.*)', 117),
]

ALL_DERIVED_ATTRIBUTES = [
  DerivedAttribute('price_indoor_sqft', 101, ['price_sqft_zillow', 'sqft', 'price', 'estimate'],
                   lambda p_z, sqft, p, e: SafeDivide(
                     p_z if p_z or ((not p and not e) or not sqft) else GetInt(p or e) / GetInt(sqft),
                     500.0)),
  DerivedAttribute('price_lot_sqft', 101.5, ['lot_size', 'price', 'estimate'],
                   lambda sqft, p, e: SafeDivide(
                     '' if not sqft or (not p and not e) else GetInt(p or e) / GetInt(sqft),
                     150.0)),
]

ALL_ATTRIBUTES = [
  PropertyAttribute('zillow_id', 1),
  PropertyAttribute('address', 8),
  PropertyAttribute('beds', 5),
  PropertyAttribute('bath', 6),
  PropertyAttribute('sqft', 7),
  PropertyAttribute('status', 2),
  PropertyAttribute('price', 3),
  PropertyAttribute('estimate', 4),
  PropertyAttribute('description', 10000),
]

for fp in ALL_FACT_PARSERS:
  ALL_ATTRIBUTES.append(PropertyAttribute(fp.name, fp.rank))
for dp in ALL_DERIVED_ATTRIBUTES:
  ALL_ATTRIBUTES.append(PropertyAttribute(dp.name, dp.rank))

ATTRIBUTES_RANKED = sorted(ALL_ATTRIBUTES, key=lambda x: x.rank)

NAME_TO_ATTRIBUTE = dict(
  [(attr.name, attr) for attr in ATTRIBUTES_RANKED])

def FromName(attr_name, attr_value):
  """Creates an attribute from the name and value.

  :param attr_name:
  :param attr_value:
  :return:
  """
  return PropertyAttributeWithValue(NAME_TO_ATTRIBUTE[attr_name], attr_value) \
      if attr_name in NAME_TO_ATTRIBUTE else None

def RenderHeaderToSpreadsheet(header_cells):
  for h in header_cells.values():
    h.value = ''

  for i, s in enumerate(ATTRIBUTES_RANKED):
    header_cells[i].value = s.name
  return header_cells
