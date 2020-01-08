"""cli methods"""

from absl.flags import argparse_flags
import argparse


# ----------------------------------------------------------------------------
def parse_cmd_dict(parser, d: dict):
  """parse an 'argparse' dictionary

  Args:
  parser (argparse.ArgumentParser or compatible): parser to which to add
  d (dict): argparse-style dictionary

  Returns:
  parser
  """

  if parser is None:  # top-level parser
    parser = argparse_flags.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        **(d['parser_kwargs']))
  else:
    parser = parser.add_parser(
        d['parser_name'],
        **(d['parser_kwargs']),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

  if 'add_arguments' in d:
    for x in d['add_arguments']:
      parser.add_argument(*(x['args']), **(x['kwargs']))

  if 'subparser' in d:
    sp = d['subparser']
    subparser = parser.add_subparsers(**(sp['kwargs']))
    subparser.required = True
    if 'parsers' in sp:
      for p in sp['parsers']:
        parse_cmd_dict(subparser, p)

  return parser


# ----------------------------------------------------------------------------
def invoke_command(args: dict, d: dict):
  """invoke callback command from argparse-style dictionary

  Args:
  args (dict): arguments dictionary
  d (dict): argparse-style dictionary

  Returns:
  result of callback invocation, None on error
  """

  if 'callback' in d:
    return d['callback'](args)

  # no command, so there must be a subparser
  if 'subparser' not in d:
    logging.error('unable to determine cli command')
    return None

  if 'kwargs' not in d['subparser']:
    logging.error('unable to process subparser')
    return None

  if 'dest' not in d['subparser']['kwargs']:
    logging.error('unable to process subparser')
    return None

  key = args[d['subparser']['kwargs']['dest']]

  if 'parsers' not in d['subparser']:
    logging.error('unable to process subparser')
    return None

  for p in d['subparser']['parsers']:
    if p['parser_name'] == key:
      return invoke_command(args, p)

  logging.error('unable to process command args')
  return None
