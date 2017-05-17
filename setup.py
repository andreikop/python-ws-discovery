#!/usr/bin/env python

try:
   from setuptools.commands import setup
except:
   from distutils.core import setup

setup(name='WSDiscovery',
      version='0.2',
      description='WS-Discovery implementation for python',
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
      py_modules=['WSDiscovery'],
      setup_requires=['netifaces']
     )
