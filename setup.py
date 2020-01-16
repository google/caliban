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


setup(
    name='caliban',
    version=with_versioneer(lambda v: v.get_version()),
    cmdclass=with_versioneer(lambda v: v.get_cmdclass(), {}),
    python_requires='>3.6.0',
    install_requires=[
        'absl-py', 'blessings', 'commentjson', 'google-api-python-client',
        'pyyaml', 'tqdm', 'kubernetes>=10.0.1', 'google-auth>=1.7.0',
        'google-cloud-core>=1.0.3', 'google-cloud-container>=0.3.0',
        'urllib3>=1.25.7', 'yaspin>=0.16.0'
    ],
    extras_require={
        # These are required for local development, but not for actually
        # running the application.
        'dev': ['python-language-server[all]', 'nose', 'hypothesis'],
    },
    packages=find_packages(),
    description='Docker-based job runner for AI research.',
    entry_points={'console_scripts': ['caliban = caliban.main:main']})
