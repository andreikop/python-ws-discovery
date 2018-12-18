#!/usr/bin/env python

import os.path

try:
   from setuptools.commands import setup
except:
   from distutils.core import setup

here = os.path.abspath(os.path.dirname(__file__))

try:
    README = open(os.path.join(here, "README.md")).read()
    CHANGES = open(os.path.join(here, "CHANGES.md")).read()
except Exception:
    README = CHANGES = ""


setup(name='WSDiscovery',
      version='1.0.0',
      description='WS-Discovery implementation for python',
      long_description=README + "\n\n" + CHANGES,
      long_description_content_type="text/markdown",
      author='Andrei Kopats',
      author_email='andrei.kopats@gmail.com',
      url='https://github.com/andreikop/python-ws-discovery.git',
      classifiers=[
            'Development Status :: 4 - Beta',
            'Environment :: Console',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)',
            'Operating System :: MacOS :: MacOS X',
            'Operating System :: POSIX :: Linux',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Topic :: Software Development :: Libraries',
            'Topic :: Software Development :: Libraries :: Python Modules',
            'Topic :: Communications'
      ],
      packages=['wsdiscovery'],
      setup_requires=['netifaces'],
      install_requires=['netifaces']
     )
