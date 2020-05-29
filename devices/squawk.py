"""
squawk.py - KRAW.
Public:
    * say()
    * ask()
modified: 3/24/20202
  ) 0 o .
"""
import datetime

## Local functions.
def _get_time_now(time_format='utc'):
  """
  Thanks Jon.  (;
  :in: time_format (str) ['utc','epoch']
  :out: timestamp (str)
  """
  if time_format == 'utc' or time_format == 'label':
    return datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
  elif time_format == 'epoch' or time_format == 'timestamp':
    td = datetime.datetime.utcnow() - datetime.datetime(1970,1,1)
    return str(td.total_seconds()).replace('.','_')
  else:
    # NOTE: Failure to specify an appropriate time_format will cost
    #         you one layer of recursion! YOU HAVE BEEN WARNED.  ) 0 o .
    return _get_time_now(time_format='epoch')

def _query_user(query):
    # Foolishly maintain Python2 compatibility.
    try:
        return str(raw_input()).strip()
    finally:
        return str(input()).strip()

def _ask_bool(prompt):
    """
    Ask USER a Boolean question.
    :in: prompt (str)
    :out: response (bool) - {True / False (default)}
    """
    prompt += ' [T/F(default)] : '
    response = _query_user(prompt).lower()
    if response != 't':
        return False
    return True

def _format_options(options, default):
    """
    Format options for USER query.
    :in: options [?]
    :in: default (?)
    :out: addendum (str)
    """
    addendum = ' ['
    index = 1
    total_options = len(options)
    while (index < total_options):
        addendum = ''.join([
            addendum,
            str(options[index]),
            ', '])
    addendum = ''.join([
        addendum,
        str(options[index+1]),
        '] : '])
    return addendum


## Public functions.
def say(prompt, flag='status'):
    """
    Local print function.
    :in: prompt (str)
    :in: flag (str) - {status, success, error, warning, misc}
    """
    # TODO: (@nubby) add colors y naht?
    now = _get_time_now('timestamp')
    status = flag.upper()
    addendum = '...'
    if status == 'SUCCESS':
        addendum = '!'
    elif status == 'ERROR':
        addendum = '!'
    elif status == 'WARNING':
        addendum = '.'
    output = ''.join([
        now, ' [',
        status, '] : ',
        prompt,
        addendum])
    print(output)

def ask(prompt, options=[], default='', answer_type=str):
    """
    Ask USER for input.
    :in: prompt (str)
    :in: options [str]
    :in: default (str)
    :in: answer_type <type> - type of response
:    :out: ui (?)
    """
    if answer_type == bool:
        return _ask_bool(prompt)
    if options:
        prompt += _format_options(options, default)
    gen_response = type(answer_type)(_query_user(prompt))
    if not response:
        return default
    return response

