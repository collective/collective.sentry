# -*- coding: utf-8 -*-
"""
collective.sentry
"""
import os
from setuptools import setup, find_packages


def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()


version = '0.2.4'

long_description = (
        read('README.rst')
        + '\n' +
        read('CHANGES.txt')
        + '\n' +
        read('CONTRIBUTORS.txt')
)

setup(name='collective.sentry',
      version=version,
      description="Sentry integration with Plone 5.2/Zope 4",
      long_description=long_description,
      # Get more strings from
      # http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
          "Framework :: Plone",
          "Intended Audience :: Developers",
          "Topic :: Software Development :: Libraries :: Python Modules",
          "License :: OSI Approved :: GNU General Public License (GPL)",
          "Programming Language :: Python",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7",
          "Framework :: Plone",
          "Framework :: Plone :: 5.2",
          "Framework :: Zope",
          "Framework :: Zope :: 4",
          "Topic :: Software Development :: Libraries :: Python Modules",
      ],
      keywords='policy',
      author='Andreas Jung',
      author_email='info@zopyx.com',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['collective', ],
      include_package_data=True,
      zip_safe=False,
      install_requires=['setuptools',
                        'sentry-sdk'
                        ],
      entry_points="""
      # -*- Entry points -*-
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
