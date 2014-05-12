#!/usr/bin/python

# See file COPYING distributed with dpf for copyright and license.

from distutils.core import setup

long_description = open('README.rst').read()

setup(name='dpf', 
      version='0.1.0', 
      description='A distributed processing framework', 
      author='Christian Haselgrove', 
      author_email='christian.haselgrove@umassmed.edu', 
      url='https://github.com/chaselgrove/dpf', 
      classifiers=['Development Status :: 3 - Alpha', 
                   'Environment :: Web Environment', 
                   'Intended Audience :: Information Technology', 
                   'Intended Audience :: Science/Research', 
                   'License :: OSI Approved :: BSD License', 
                   'Operating System :: OS Independent', 
                   'Programming Language :: Python', 
                   'Topic :: Scientific/Engineering', 
                   'Topic :: System :: Distributed Computing'], 
      license='BSD license', 
      long_description=long_description
     )

# eof
