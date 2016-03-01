"""Data model for a single property.
"""

import attributes
import zillow_api_wrapper as zaw


class Property(object):

  def __init__(self, property_attributes):
    self.property_attributes = property_attributes

  def __repr__(self):
    return str(self.property_attributes)

  @staticmethod
  def FromSpreadsheet(header, spreadsheet_cells):
    """Creates a property object from the provided spreadsheet attributes.
    """
    attrs = []
    for i, cell in enumerate(spreadsheet_cells.values()):
      if cell.value:
        a = attributes.FromName(header[i].value, cell.value)
        if a:
          attrs.append(a)
    return Property(attributes.PropertyAttributes(attrs))

  def RenderToSpreadsheet(self, spreadsheet_cells):
    self.property_attributes.RenderToSpreadsheet(spreadsheet_cells)
    return spreadsheet_cells

  def LoadFromZillow(self):
    """Loads the property data from Zillow.
    """
    zillow_attrs = zaw.LoadZillowProperty(
      self.property_attributes.GetValue('zillow_id'))
    self.property_attributes.Merge(zillow_attrs)

def ParseFromSpreadsheet(spreadsheet_cells):
  """Parses into a list of Property objects from the spreadsheet data.
  """
  return [Property.FromSpreadsheet(spreadsheet_cells[0], spreadsheet_cells[r+1])
          for r in xrange(len(spreadsheet_cells) - 1)]

def RenderToSpreadsheet(properties, all_cells):
  """Render the properties objects to spreadsheet cells.

  :param properties:
  :return:
  """
  rows = {0: attributes.RenderHeaderToSpreadsheet(all_cells[0])}
  for i, p in enumerate(properties):
    rows[i + 1] = p.RenderToSpreadsheet(all_cells[i+1])
  return rows
