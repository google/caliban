"""
Commands to generate a grid search.
"""
from __future__ import absolute_import, division, print_function

import itertools

import numpy as np
from absl import logging


def param_id_name(metaconf):
  """Gets the PARAM_ID name out of the metaconfig.

  TODO take care of there case where there is no PARAM_ID..."""
  name = 'loopvar'

  param_ids = metaconf['param_id']

  if isinstance(param_ids, str):
    name = param_ids
  elif len(param_ids) == 1:
    name = param_ids[0]

  return name


def get_param_ids(metaconf):
  """Extract the param IDs from the config in the proper format."""
  param_ids = metaconf['param_id']
  if isinstance(param_ids, str):
    param_ids = [param_ids]

  return param_ids


def get_hyper(conf, metaconf, param_id):
  """If you specified that the param is something you want to work with... then
you would have had to include it under the 'param_id' thing in your config.

  The value can be one of ['list', 'log2', 'lin']

  If you do that, we'll go ahead and look for lots of different keys in your
  config.
  """
  hyper = None

  if 'hyper' + param_id in metaconf:
    hyper = metaconf['hyper' + param_id]
  elif 'hyper' + param_id in conf:
    hyper = conf['hyper' + param_id]
  else:
    logging.info('Should specify hyper' + param_id)

  return hyper


def process_hyper(conf, param_id, hyper):
  """
  Process a specific hyperparameter"""
  ret = None
  if hyper == 'list':
    ret = conf[param_id + '_list']
  else:
    if conf['max' + param_id] == -1:
      if conf['num_samples'] == -1:
        raise ValueError('Not supported.')
      else:
        print('Setting max to number of samples')
        conf['max' + param_id] = conf['num_samples']

    if hyper == 'log2':
      ret = np.logspace(np.log2(conf['min' + param_id]),
                        np.log2(conf['max' + param_id]),
                        num=conf['num' + param_id],
                        base=2)
    elif hyper == 'lin':
      ret = np.linspace(conf['min' + param_id],
                        conf['max' + param_id],
                        num=conf['num' + param_id])
  return ret


def generate_job_configurations(conf, metaconf):
  """This one, I'm also not sure of yet.

  param_id is a parameter name that we want to actually distribute out. Without
  id we just do a fixed run.
  """

  par_list = []

  for param_id in get_param_ids(metaconf):
    hyper = get_hyper(conf, metaconf, param_id)
    if hyper is None:
      continue
    par_list.append(process_hyper(conf, param_id, hyper))

  # This is the list of settings for the hyper-params, in the order presented in
  # the param_id list.
  par_list = [list(el) for el in list(itertools.product(*par_list))]

  # This is the total number of combinations.
  print('Total of ', len(par_list), ' combinations of settings')

  # Integer division to get the number of total jobs that we want to distribute.
  n = (len(par_list) - 1) // conf['numjobs'] + 1

  # Here's the formatted thing:
  # List[Job[HyperParams]]; each is a nested list.
  par_listf = [
      par_list[i * n:(i + 1) * n] for i in range((len(par_list) + n - 1) // n)
  ]

  # Then this joins the hyper-params with a +, so the final format is:
  #
  # List[List[String]]
  #
  # Outer List is a list of submissions.
  # Inner list is a list of the hyperparam strings that each job should execute.
  par_listf = [
      ['+'.join([str(elc) for elc in elb]) for elb in el] for el in par_listf
  ]

  return par_listf


def submit_remote(conf, metaconf, args):
  print("Placeholder!")


def remote_submit_loop(par_listf, args0, conf, metaconf):
  """Submit all jobs in the distributed world."""
  total_jobs = len(par_listf)

  for k, job_param_list in enumerate(par_listf, start=1):
    args = args0

    if 'param_id' in metaconf:
      name = param_id_name(metaconf)

      # Note that this currently is using old style string formatting.
      logging.info("")
      logging.info(
          '>> Sending job {:.0f} out of {:.0f}'.format(k, total_jobs) +
          ' with ' + name + ':', job_param_list)
      logging.info("")

      args = args + ['-' + name + '_list=' + ','.join(job_param_list)]

    if k == total_jobs and 'special_last' in conf:
      args += [conf['special_last']]

    submit_remote(conf, metaconf, args)
