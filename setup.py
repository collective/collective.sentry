# -*- coding: utf-8 -*-
"""
collective.sentry - Policy Package for http://www.ugent.be
"""
import os
from setuptools import setup, find_packages

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

version = '43.12.dev0'

long_description = (
    read('README.txt')
    + '\n' +
    read('CHANGES.txt')
    + '\n' +
    read('ugent', 'policy', 'README.txt')
    + '\n' +
    read('CONTRIBUTORS.txt')
    )

tests_require=['zope.testing']

setup(name='collective.sentry',
      version=version,
      description="Policy-package for the main portal-site of Ghent University",
      long_description=long_description,
      # Get more strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
        'Framework :: Plone',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        ],
      keywords='policy',
      author='UGent Portaalteam',
      author_email='portaal@ugent.be',
      url='https://trac.portaal.ugent.be/wiki/Packages/collective.sentry',
      license='GPL',
      packages=find_packages(exclude=['ez_setup']),
      namespace_packages=['ugent', ],
      include_package_data=True,
      zip_safe=False,
      install_requires=['setuptools',
                        'ugent.vocabularies'
                        ],
      tests_require=tests_require,
      extras_require=dict(tests=tests_require),
      test_suite = 'collective.sentry.tests.test_docs.test_suite',
      entry_points="""
      # -*- Entry points -*-
      [z3c.autoinclude.plugin]
      target = plone
      """,
      )
