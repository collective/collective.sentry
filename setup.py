# -*- coding: utf-8 -*-
"""
collective.sentry
"""
import os
from setuptools import setup, find_packages


def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()


version = '0.3.2'

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
          "Development Status :: 4 - Beta",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: GNU General Public License (GPL)",
          "Programming Language :: Python",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: 3.8",
          "Programming Language :: Python :: 3.9",
          "Programming Language :: Python :: 3.10",
          "Programming Language :: Python :: 3.11",
          "Framework :: Plone",
          "Framework :: Plone :: 5.2",
          "Framework :: Plone :: 6.0",
          "Framework :: Zope",
          "Framework :: Zope :: 4",
          "Framework :: Zope :: 5",
          "Topic :: Software Development :: Libraries :: Python Modules",
      ],
      keywords='policy',
      author='Andreas Jung',
      author_email='info@zopyx.com',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['collective', ],
      include_package_data=True,
      project_urls={
        "Code": "https://github.com/collective/collective.sentry",
        "Tracker": "https://github.com/collective/collective.sentry/issues",
      },
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
