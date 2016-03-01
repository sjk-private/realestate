"""Wraps the basic Google Spreadsheets API with Pythonic functions.
"""

import json
import gspread
from oauth2client.client import SignedJwtAssertionCredentials
from collections import defaultdict as dd

GSPREAD_CLIENT = None

def Initialize():
  json_key = json.load(open('/Users/sjeyakumar/sanjay/personal/realestate/data_updater/RealEstate_Data_Consume-2f5691622669.json'))
  scope = ['https://spreadsheets.google.com/feeds']

  credentials = SignedJwtAssertionCredentials(json_key['client_email'], json_key['private_key'], scope)

  global GSPREAD_CLIENT
  GSPREAD_CLIENT = gspread.authorize(credentials)

def OpenSpreadsheet(name):
  """Opens the provided spreadsheet.
  """
  return GSPREAD_CLIENT.open(name)

def ReadRow(spreadsheet, row_num):
  """Reads the specified row number from the spreadsheet.
  """
  return spreadsheet.sheet1.row_values(row_num)

def ReadCells(worksheet, start_row, end_row):
  """Read the cells for the provided row numbers.

  Args:
    worksheet
    start_row     - Row number (1-based) and inclusive.
    end_row       - Row number (1-based) and exclusive.
  """
  cells_as_array = dd(lambda: dd(str))
  cells = worksheet.range('A%s:Z%s' % (start_row, (end_row-1)))
  for c in cells:
    cells_as_array[c.row-1][c.col-1] = c
  return cells_as_array

def WriteCells(worksheet, data_cells):
  """Write the provided cells.
  """
  all_cells = []
  for row in data_cells.values():
    all_cells.extend(row.values())

  worksheet.update_cells(all_cells)

def ReadAllRows(spreadsheet):
  """Read all the rows from the provided spreadsheet.
  """
  return spreadsheet.sheet1.get_all_values()

def LoadSpreadsheet(
  name,
  sheet_name,
  row_batch_size=10):
  """Loads the provided spreadsheet.
  """
  spreadsheet = OpenSpreadsheet(name)
  worksheet = GetWorksheet(spreadsheet, sheet_name)
  all_cells = None
  for i in xrange(100):
    start_row = 1+(i*row_batch_size)
    cells = ReadCells(worksheet, start_row, start_row+row_batch_size)

    # Check if there are empty rows.
    empty_rows = []
    for row in cells.keys():
      is_empty = True
      for col in cells[row].keys():
        if cells[row][col].value:
          is_empty = False
          break
      if is_empty:
        empty_rows.append(row)

    # Delete the empty rows.
    for row in empty_rows:
      del cells[row]

    # Update all cells.
    if not all_cells:
      all_cells = cells
    else:
      all_cells.update(cells)

    # Break, if there were empty rows.
    if empty_rows:
      break

  return all_cells

def WriteSpreadsheet(
  name,
  sheet_name,
  all_cells):
  """Writes the provided spreadsheet.
  """
  spreadsheet = OpenSpreadsheet(name)
  worksheet = GetWorksheet(spreadsheet, sheet_name)
  WriteCells(worksheet, all_cells)

def GetWorksheet(spreadsheet, sheet_name):
  """Returns a worksheet object with the provided sheet name.
  """
  return filter(lambda x: x.title == sheet_name, spreadsheet.worksheets())[0]

if __name__ == '__main__':
  Initialize()

  spreadsheet = OpenSpreadsheet('Real Estate')
  import code
  vars = globals()
  vars.update(locals())
  shell = code.InteractiveConsole(vars)
  shell.interact()

  spreadsheet.sheet1.update_acell('B2', "it's down there somewhere, let me take another look.")

