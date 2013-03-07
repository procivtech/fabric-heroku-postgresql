import fabric_heroku_postgresql

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

packages = ['fabric_heroku_postgresql']
requires = open('requirements.txt').read().split("\n")

setup(
        name='fabric_heroku_postgresql',
        version=fabric_heroku_postgresql.__version__,
        author="Mike Matz",
        author_email="mike@simplegov.com",
        copyright="Copyright 2013 SimpleGov",
        license=open('LICENSE').read(),
        install_requires=requires,
        description="Fabric helpers for heroku-postgresql",
        long_description=open('README.md').read(),
        package_data={'': ['LICENSE']},
        package_dir={'fabric_heroku_postgresql': 'fabric_heroku_postgrseql'},
        )
