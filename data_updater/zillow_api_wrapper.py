"""Wraps the basic Zillow API with Pythonic functions.
"""

#ZW = ZillowWrapper('X1-ZWz1a88dskxa17_5kvb6')

import attributes

from bs4 import BeautifulSoup
from misc_util import Bunch
import net_util
import string

def ws(text):
  """Clean up whitespace in provided text.
  """
  return ' '.join(text.split())

def fb_meta(bs, name):
  """Return the FB meta attribute.
  """
  return bs.find('meta', {'property':name}).attrs['content']

def Initialize():
  """Initializes the Zillow API wrapper.
  """
  pass

def LoadZillowProperty(zpid):
  """Loads the information for the provided property.

  Args:
    zpid - Zillow property id.

  Returns:
    A Bunch with the property attributes.
  """
  print 'Loading: ', zpid
  if '_' in zpid:
    zpid = zpid.split('_')[0]
  url = 'http://www.zillow.com/homedetails/%s_zpid/' % zpid

  c = net_util.GenericFetchFromUrlToString(
    url,
    user_agent=net_util.CHROME_USER_AGENT)

  if c.status_code != 200:
    return None

  bs = BeautifulSoup(c.body)

  main = bs.find('div', role='main')

  entity_info = Bunch()
  entity_info.address = fb_meta(bs, 'og:zillow_fb:address')

  bbs = main.findAll('span', class_='addr_bbs')
  try:
    entity_info.beds = fb_meta(bs, 'zillow_fb:beds')
    entity_info.bath = fb_meta(bs, 'zillow_fb:baths')
    entity_info.sqft = ws(bbs[2].text)
  except Exception:
    import code
    vars = globals()
    vars.update(locals())
    shell = code.InteractiveConsole(vars)
    shell.interact()

  price_info = main.find('div', {'id':'home-value-wrapper'})
  entity_info.status = ws(price_info.find('div', class_='status-icon-row').text)
  entity_info.price = ws(price_info.find('div', class_='main-row').text)
  if entity_info.price == 'Off Market':
    entity_info.price = ''
  estimate = ws(main.findAll('div', class_='zest-value')[0].text)
  entity_info.estimate = estimate.split(':')[1].strip() if ':' in estimate else estimate

  entity_info.description = ws(fb_meta(bs, 'zillow_fb:description'))
  facts_div = main.find('div', class_='hdp-facts')
  entity_info.facts = '; '.join([ws(f.text) for f in facts_div.findAll('li')])

  _PopulateFromFacts([ws(f.text) for f in facts_div.findAll('li')], entity_info)

  _PopulateDerivedAttributes(entity_info)

  for attr in ('description', 'facts'):
    val = getattr(entity_info, attr, None)
    if val:
      val = filter(lambda x: x in string.printable, val)
    setattr(entity_info, attr, val)

  return _ToPropertyAttributes(entity_info)


_ALL_FACT_NAMES = [fp.name for fp in attributes.ALL_FACT_PARSERS]

def _PopulateFromFacts(facts_list, entity_info):
  """Populates specific facts from the provided list on the webpage.
  """
  for name in _ALL_FACT_NAMES:
    setattr(entity_info, name, '')

  for fact in facts_list:
    for parser in attributes.ALL_FACT_PARSERS:
      x = parser.Parse(fact)
      if x:
        setattr(entity_info, parser.name, x)

def _PopulateDerivedAttributes(entity_info):
  """Populates attributes derived from the scraped data.
  """
  for a in attributes.ALL_DERIVED_ATTRIBUTES:
    setattr(entity_info, a.name, '')

  for a in attributes.ALL_DERIVED_ATTRIBUTES:
    vals = [getattr(entity_info, requested, '') for requested in a.attrs]
    setattr(entity_info, a.name, a.fn(*vals))

def _ToPropertyAttributes(entity_info):
  """Convert the provided bag of entity_info attributes to a Property object.

  :param entity_info:
  :return:
  """
  attrs = []
  for k in entity_info.keys():
    if k in attributes.NAME_TO_ATTRIBUTE:
      attrs.append(attributes.PropertyAttributeWithValue(
        attributes.NAME_TO_ATTRIBUTE[k],
        getattr(entity_info, k)))

  return attributes.PropertyAttributes(attrs)

if __name__ == '__main__':

  print LoadZillowProperty('24838363')

  import code
  vars = globals()
  vars.update(locals())
  shell = code.InteractiveConsole(vars)
  shell.interact()

