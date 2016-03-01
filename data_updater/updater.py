"""Script that updates the properties in the Spreadsheet with the most
current information.
"""

import google_sheets_wrapper as gsw
import zillow_api_wrapper as zaw
import property

_SPREADSHEET_NAME = 'Real Estate'
_BATCH_ROWS = 10
_BUY_SHEET_NAME = 'Buy'
_RENT_SHEET_NAME = 'Rent'

def UpdateSheet():
  """Updates the spreadsheet with the current real-estate data.
  """
  for sheet_name in (
    _BUY_SHEET_NAME,
    _RENT_SHEET_NAME,
    ):
    all_cells, properties = _LoadSpreadsheetData(sheet_name)
    _LoadCurrentData(properties)
    _WriteSpreadsheetData(sheet_name, properties, all_cells)

def _LoadSpreadsheetData(sheet_name):
  """Load the current data from the spreadsheet.
  """
  all_cells = gsw.LoadSpreadsheet(_SPREADSHEET_NAME, sheet_name)
  return all_cells, property.ParseFromSpreadsheet(all_cells)

def _LoadCurrentData(properties):
  """Loads the current property details from Zillow.
  """
  for p in properties:
    p.LoadFromZillow()

def _WriteSpreadsheetData(sheet_name, properties, all_cells):
  """Write the data to the spreadsheet.
  """
  all_cells = property.RenderToSpreadsheet(properties, all_cells)
  gsw.WriteSpreadsheet(_SPREADSHEET_NAME, sheet_name, all_cells)

if __name__ == '__main__':
  gsw.Initialize()
  zaw.Initialize()

  UpdateSheet()
