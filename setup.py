from setuptools import find_packages, setup


def with_versioneer(f, default=None):
  """Attempts to execute the supplied single-arg function by passing it
versioneer if available; else, returns the default.

  """
  try:
    import versioneer
    return f(versioneer)
  except ModuleNotFoundError:
    return default


def readme():
  try:
    with open('README.md') as f:
      return f.read()
  except Exception:
    return None


REQUIRED_PACKAGES = [
    'absl-py',
    'blessings',
    'commentjson',
    'google-api-python-client',
    'pyyaml',
    'tqdm',
    'kubernetes>=10.0.1',
    'google-auth>=1.7.0',
    'google-cloud-core>=1.0.3',
    'google-cloud-container>=0.3.0',
    'urllib3>=1.25.7',
    'yaspin>=0.16.0',
    # This is not a real dependency of ours, but we need it to override the
    # dep that commentjson brings in. Delete once this is merged:
    # https://github.com/vaidik/commentjson/pull/33/files
    'lark-parser>=0.7.1,<0.8.0',
    'SQLAlchemy>=1.3.11',
]

setup(name='caliban',
      version=with_versioneer(lambda v: v.get_version()),
      cmdclass=with_versioneer(lambda v: v.get_cmdclass(), {}),
      description='Docker-based job runner for AI research.',
      long_description=readme(),
      python_requires='>=3.5.3',
      author='Blueshift Team',
      author_email='samritchie@google.com',
      url='https://team.git.corp.google.com/blueshift/caliban',
      packages=find_packages(exclude=('tests', 'docs')),
      install_requires=REQUIRED_PACKAGES,
      include_package_data=True,
      entry_points={
          'console_scripts': [
              'caliban = caliban.main:main',
              'expansion = caliban.expansion:main'
          ]
      })
