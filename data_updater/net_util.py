"""Utility functions for various network-y things.
"""

from collections import namedtuple
from cStringIO import StringIO
import errno
import os
import mimetools
import mimetypes
import socket
import stat
import struct
import subprocess
import sys
import tempfile
import threading
import urllib
import urllib2
import urlparse

from SocketServer import BaseServer
from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from SocketServer import ForkingMixIn

CHROME_USER_AGENT = \
  'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_4; en-US) AppleWebKit/534.7' \
  ' (KHTML, like Gecko) Chrome/7.0.517.44 Safari/534.7 (Tellapart)'

from tellapart.third_party import keepalive
from tellapart.util import misc_util

# How much data to read at a time in GenericFetchFromUrl() and its variants.
_HTTP_READ_BUFFER_SIZE = 1024 * 1024

# Options for running CurlFetchFromUrlToFile.
CurlOptsType = namedtuple('CurlOpts', ['connect_timeout', 'max_elapsed_time'])

def CurlOpts(connect_timeout=None, max_elapsed_time=None):
  return CurlOptsType(connect_timeout=connect_timeout,
                      max_elapsed_time=max_elapsed_time)

def GenericFetchFromUrlToString(
      url,
      headers=None,
      post_data=None,
      follow_redirects=True,
      keep_alive=False,
      basic_auth=False,
      user_agent=None,
      username=None,
      password=None,
      timeout_secs=None,
      http_method=None):
  """A more generic form of FetchFromUrlToString().

  This function supports GET/POST requests and returns response headers and
  status codes.

  Args:
    url - The URL from which to fetch.
    headers - A dictionary of request headers, or None.
    post_data - A raw data string, or a dictionary or sequence of two-element
                tuples representing POST data keys/values.  If None (default),
                makes a GET request.  To make a POST request with no data,
                submit a value of {}.  If files are included, they will be sent
                as a multipart message.  For example, if presented with
                {"modify" : "0", "file" : open(filename, "rb")}
                the "modify" parameter will be sent as a POST param, and
                "file" will be uploaded as part of a MIME message.
                This parameter can also be a raw string, in which case it will
                be sent without processing as the POST data.
    follow_redirects - Whether to automatically follow redirects (HTTP 30x).
                       Default: True.
    keep_alive - Whether to set the 'Connection' request header to 'Keep-Alive'.
                 Default: False.
    basic_auth - Whether to use basic HTTP authentication to make the request.
                 If True, the username and password params should be provided.
    user_agent - The user agent to use for this request, Uses the python
                default Python/2.6 string if None
    username - The username used for basic HTTP authentication, if needed.
    password - The password used for basic HTTP authentication, if needed.
    timeout_secs - If present, the number of seconds after which to timeout the
                   request.
    http_method - If present, use this http method instead of the default.

  Returns
    A Bunch object representing the response, containing the attributes:
      * body - The HTTP response body string.
      * headers - An httplib.HTTPMessage (dict-like) object containing the
                  response headers.
      * status_code - The HTTP response status code (e.g., 200, 404, etc.).
      * final_url - The real URL of the page.  In some cases, the server may
                    redirect the client to a different URL, so this value may
                    differ from that of the 'url' argument.
  """
  body_buffer = StringIO()
  try:
    result = _GenericFetchFromUrl(
        url,
        body_buffer,
        headers,
        post_data,
        follow_redirects,
        keep_alive=keep_alive,
        basic_auth=basic_auth,
        user_agent=user_agent,
        username=username,
        password=password,
        timeout_secs=timeout_secs,
        http_method=http_method)

    result.body = body_buffer.getvalue()
  finally:
    body_buffer.close()

  return result

def FetchFromUrlToString(url, user_agent=None, timeout_secs=None):
  """Retrieves content from the given URL and returns it as a string.

  Args:
    url - The URL from which to fetch.
    user_agent - The user agent to use for this request, Uses the python
                default Python/2.6 string if None
    timeout_secs - If present, the number of seconds after which to timeout the
                   request.
  Returns
    A content string.
  """
  result = GenericFetchFromUrlToString(url, user_agent=user_agent,
                                       timeout_secs=timeout_secs)
  if result.status_code != 200:
    raise Exception('Error fetching URL content: %s' % result)

  return result.body

def FetchFromUrlToTempFile(url, num_tries=1,
                           retry_on_error_codes=frozenset([500, 503]),
                           user_agent=None, dir=None, timeout_secs=None):
  """Retrieves content from the given URL and saves it as a temporary local
  file.

  Args:
    url - The URL from which to fetch.
    num_tries - Number of times to try to fetch this URL.
                A URL is re-fetched if the error code is in
                retry_on_error_codes.
    retry_on_error_codes - The set of error codes for which we should try
                           to refetch a URL.
    user_agent - The user agent to use for this request, Uses the python
                default Python/2.6 string if None
    dir - If specified, the file will be created in this directory.  If the
          directory doesn't exist, create it.
    timeout_secs - If present, the number of seconds after which to timeout the
                   request.

  Returns
    A (file, headers) tuple.  'file' is a file-like object representing a
    temporary file from which the fetched content can be read.  When this object
    is closed (either explicitly with a close() call or implicitly when it goes
    out of scope and is garbage collected), the file will be deleted.
    'headers' is a dict of HTTP response headers.

    If dir is not specified, then the 'file' object will not be written to disk,
    which is must faster. However, use caution when using this option in case
    the fetched contents are very large.
  """
  if dir:
    try:
      os.makedirs(dir)
    except OSError, e:
      if e.errno != errno.EEXIST:
        raise

    f = tempfile.TemporaryFile(dir=dir)
  else:
    f = StringIO()

  for i in xrange(num_tries):
    result = _GenericFetchFromUrl(url, body_output=f, user_agent=user_agent,
                                  timeout_secs=timeout_secs)
    if result.status_code not in retry_on_error_codes:
      break
  if result.status_code != 200:
    raise Exception('Error fetching URL content: %s' % result)

  f.seek(0)
  return (f, result.headers)

def FetchFromUrlToFile(url, local_filename, keep_alive=False, user_agent=None):
  """Retrieves content from the given URL and saves it as a named local file.

  Args:
    url - The URL from which to fetch.
    local_filename - The name of the file to save to.
    keep_alive - Whether to keep the HTTP connection alive.  This is useful when
                 the connection must be kept open for a long time to fetch a
                 large file and the server would otherwise close the connection
                 prematurely.
    user_agent - The user agent to use for this request, Uses the python
                default Python/2.6 string if None

  Returns
    A dict of HTTP response headers.
  """
  with open(local_filename, 'w+b') as f:
    result = _GenericFetchFromUrl(url, body_output=f, keep_alive=keep_alive,
                                  user_agent=user_agent)
    if result.status_code != 200:
      raise Exception('Error fetching URL content: %s' % result)

    return result.headers

def CurlFetchFromUrlToFile(url, local_filename, curl_opts):
  """Fetch a URL to a file using curl.

  Args:
    url - Url to fetch.
    local_filename - File to write it to.
    curl_opts - A CurlOpts with configuration to run curl with. Params:
                 - connect_timeout - If not None, maximum time in seconds that
                                     you allow the connection to the server to
                                     take.
                 - max_elapsed_time - If not None, Maximum time in seconds that
                                      you allow the whole operation to take.

  Returns:
    True iff the curl command succeeded.
  """
  cmd = ['curl', '--silent']
  # Possibly apply some limits on how long curl should take to connect and how
  # long the total operation should take.
  if curl_opts.connect_timeout is not None:
    cmd += ['--connect-timeout', str(curl_opts.connect_timeout)]
  if curl_opts.max_elapsed_time is not None:
    cmd += ['--max-time', str(curl_opts.max_elapsed_time)]
  cmd.append(url)

  with open(local_filename, 'w+b') as f:
    retcode = subprocess.call(cmd, stdout=f, stderr=sys.stderr)
    return (retcode == 0)

class _NoRedirectHandler(urllib2.HTTPRedirectHandler):
  """A subclass of urllib2.HTTPRedirectHandler that does *not* follow redirects.
  Use via _NO_REDIRECT_OPENER.
  """
  def redirect_request(self, req, fp, code, msg, hdrs, newurl):
    return None

class _MultipartPostHandler(urllib2.BaseHandler):
  """A subclass of urllib2.BaseHandler that allows for the use of multipart
  form-data to POST files to a remote server.  This handler also supports
  generic POST key-value pairs.  If there are no values to be included, then
  a GET request will be performed instead.
  """

  # BaseHandler subclasses can change the handler_order member variable to modify its
  # position in the handler list.  The post handler should run before other default
  # handlers.
  handler_order = urllib2.HTTPHandler.handler_order - 1

  def http_request(self, request):
    """Override the http_request() processing.  Retrieve the data and files to
    be posted, and create the data blob to send to the server.

    The necessary Content-Type headers will also be added.
    """
    data = request.get_data()
    if data is not None and type(data) == dict:
      v_files = []
      v_vars = []
      try:
        for key, value in data.iteritems():
          if type(value) == file:
            v_files.append((key, value))
          else:
            v_vars.append((key, value))
      except TypeError:
        systype, value, traceback = sys.exc_info()
        raise TypeError, "not a valid non-string sequence or mapping object", traceback

      if len(v_files) == 0:
        data = urllib.urlencode(v_vars)
      else:
        boundary, data = self._MultipartEncode(v_vars, v_files)
        contenttype = 'multipart/form-data; boundary=%s' % boundary
        request.add_unredirected_header('Content-Type', contenttype)

      request.add_data(data)

    elif data is not None and isinstance(data, basestring):
      request.add_data(data)

    return request

  https_request = http_request

  def _MultipartEncode(self, vars, files, boundary=None, buf=None):
    """Given the provided POST variables, and files, will encode the data
    as a multipart message if files is present.

    Args:
      vars - List of POST keys that should be sent in request
      files - List of files that should be sent in the request
      boundary - Boundary to be used to send the MIME request
      buf - Buffer to use to construct the message data

    Returns:
      Tuple of the chosen boundary and the buffer containing the message data.
    """
    if boundary is None:
      boundary = mimetools.choose_boundary()

    if buf is None:
      buf = StringIO()

    for key, value in vars:
      buf.write('--%s\r\n' % boundary)
      buf.write('Content-Disposition: form-data; name="%s"' % key)
      buf.write('\r\n\r\n' + value + '\r\n')

    for key, fd in files:
      file_size = os.fstat(fd.fileno())[stat.ST_SIZE]
      filename = fd.name.split('/')[-1]
      contenttype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
      buf.write('--%s\r\n' % boundary)
      buf.write('Content-Disposition: form-data; name="%s"; filename="%s"\r\n' % (key, filename))
      buf.write('Content-Type: %s\r\n' % contenttype)
      fd.seek(0)
      file_size = os.fstat(fd.fileno())[stat.ST_SIZE]

      # Commenting out Content-Length for now, as it's not required, and there
      # have been cases when I've seen erroneous lengths.
      # buf.write('Content-Length: %s\r\n' % file_size)

      buf.write('\r\n' + fd.read() + '\r\n')

    buf.write('--' + boundary + '--\r\n\r\n')
    buf = buf.getvalue()
    return boundary, buf

_MULTIPART_NO_REDIRECT_OPENER = urllib2.build_opener(
  _MultipartPostHandler, _NoRedirectHandler)
_MULTIPART_OPENER = urllib2.build_opener(_MultipartPostHandler)
_KEEPALIVE_OPENER = urllib2.build_opener(keepalive.HTTPHandler)

def _GenericFetchFromUrl(url, body_output, headers=None, post_data=None,
                        follow_redirects=True, keep_alive=False,
                        basic_auth=False, user_agent=None, username=None,
                        password=None, timeout_secs=None, http_method=None):
  """A generic HTTP fetcher.

  This function supports GET/POST requests and returns response headers and
  status codes.

  Args:
    url - The URL from which to fetch.
    body_output - A file-like object to which the HTTP response body will be
                  written.
    headers - A dictionary of request headers, or None.
    post_data - A raw data string, or a dictionary or sequence of two-element
                tuples representing POST data keys/values.  If None (default),
                makes a GET request.  To make a POST request with no data,
                submit a value of {}.  If files are included, they will be sent
                as a multipart message.  For example, if presented with
                {"modify" : "0", "file" : open(filename, "rb")}
                the "modify" parameter will be sent as a POST param, and
                "file" will be uploaded as part of a MIME message.
                This parameter can also be a raw string, in which case it will
                be sent without processing as the POST data.
    follow_redirects - Whether to automatically follow redirects (HTTP 30x).
                       Default: True.
    keep_alive - Whether to set the 'Connection' request header to 'Keep-Alive'.
                 Default: False.
    basic_auth - Whether to use basic HTTP authentication to make the request.
                 If True, the username and password params should be provided.
    user_agent - The user agent to use for this request, Uses the python
                default Python/2.6 string if None
    username - The username used for basic HTTP authentication, if needed.
    password - The password used for basic HTTP authentication, if needed.
    timeout_secs - If present, the number of seconds after which to timeout the
                   request.
    http_method - If present, use this http method instead of the default.

  Returns
    A Bunch object representing the response, containing the attributes:
      * headers - An httplib.HTTPMessage (dict-like) object containing the
                  response headers.
      * status_code - The HTTP response status code (e.g., 200, 404, etc.).
      * final_url - The real URL of the page.  In some cases, the server may
                    redirect the client to a different URL, so this value may
                    differ from that of the 'url' argument.
  """
  result = misc_util.Bunch(body=None, headers=None, status_code=None,
                           final_url=None, exc=None)

  headers = headers or {}

  if user_agent:
    # Add a dummy User Agent as many sites block requests with invalid
    # user agent
    headers['User-Agent'] = user_agent

  try:
    if basic_auth and username and password:
      opener = _GetHTTPBasicAuthOpener(url, username, password)
    elif keep_alive:
      headers['Connection'] = 'Keep-Alive'
      opener = _KEEPALIVE_OPENER
    elif follow_redirects:
      opener = _MULTIPART_OPENER
    else:
      opener = _MULTIPART_NO_REDIRECT_OPENER

    request = urllib2.Request(url, post_data, headers)

    if http_method:
      request.get_method = lambda: http_method

    f = opener.open(request, timeout=timeout_secs)
    try:
      result.headers = f.info()
      result.status_code = f.code
      result.final_url = f.geturl()

      _ReadHttpBodyContent(f, body_output)

    finally:
      f.close()
  except urllib2.HTTPError as e:
    result.headers = e.info()
    result.status_code = e.code
    result.final_url = e.geturl()
    result.exc = e

    _ReadHttpBodyContent(e, body_output, catch_http_error=True)

  except IOError as e:
    result.headers = None
    result.status_code = 503
    result.final_url = None
    result.exc = e

  return result

def _ReadHttpBodyContent(input_file, output_file, catch_http_error=False):
  """Read HTTP response body content from 'input_file' in chunks of size
  _HTTP_READ_BUFFER_SIZE.

  Args:
    input_file - A file-like object from which HTTP response body content bytes
                 can be read.
    output_file - A file-like object to which the read body content bytes should
                  be written.
    catch_http_error - If True, silently catch HTTPError exceptions.  This
                       should only be set to True if _ReadHttpBodyContent() is
                       called from within an exception handler for an HTTPError
                       that already occurred. (default: False)
  """
  try:
    while True:
      body_chunk = input_file.read(_HTTP_READ_BUFFER_SIZE)
      if body_chunk:
        output_file.write(body_chunk)
      if len(body_chunk) < _HTTP_READ_BUFFER_SIZE:
        break
  except urllib2.HTTPError, e:
    if not catch_http_error:
      raise e

