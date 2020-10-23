"""Pre-build and pre-run hooks, written as python functions
Each function is a separate hook, that can be enabled
or disabled by adding or removing the function name from
the pre_build_hooks or pre_run_hooks entry in the .calibanconfig.json file

Notes:
  1.  Hook names must begin with 'hook_'
  2.  Helper function names should not begin with 'hook_'
  3.  Pre-build hooks should take no arguments and return a dict
  4.  Pre-run hooks should take a single argument, the container_id
          to be used in the run, and return a dict"""

from typing import Dict
from git import Repo
from absl import logging
import subprocess
import json


def hook_gitcleanliness() -> Dict[str, str]:
  # TODO change the str, str type annotation to a custom type which is more
  # descriptive
  """
  Checks that the git repo is clean, meaning:
    1. There are no untracked files
    2. All changes are committed, i.e. there are no
        a. tracked files with unstaged changes
        b. tracked files with staged but uncommitted changes
  If the repo is clean, grabs and returns the current commit hash,
    i.e. the one which HEAD currently points to.

  Returns:
    git_clean_status - Dict[str,str] with items:
      'Succeeded': bool, whether or not the hook passed
      If 'Succeeded':
        'Data': Dict[str,str] containing
          {'commit_hash': commit_hash}
      If not 'Succeeded':
        'Error': str, the error message to output
  """
  repo = Repo('.')
  if len(repo.untracked_files) != 0:
    return {
        'Succeeded':
            False,
        'Error':
            """Git repository has untracked files.  Either add them to .gitignore, or stage and commit them."""
    }
  elif repo.is_dirty():
    return {
        'Succeeded':
            False,
        'Error':
            """Git repository is dirty.  Some tracked files have changes which are not committed."""
    }
  else:
    commit_hash = repo.commit().hexsha
    return {'Succeeded': True, 'Data': {'commit': commit_hash}}


def hook_getcontainerhash(container_id: str) -> Dict[str, str]:
  """Gets the git commit hash associated with the given container_id.
  This hash must have been stored, by a pre_build_hook as a label
  attached to the container"""
  output = subprocess.run(['docker', 'inspect', container_id],
                          capture_output=True)
  labels = json.loads(output.stdout)[0]['ContainerConfig']['Labels']
  if 'commit' in labels.keys():
    return {'Succeeded': True, 'Data': {'commit': labels['commit']}}
  else:
    return {
        'Succeeded':
            False,
        'Error':
            f'Docker image {container_id} does not contain a git commit label.'
    }
