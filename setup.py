"""
collective.sentry
"""

from setuptools import find_packages
from setuptools import setup

import os


def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()


version = "1.0.0.dev0"

long_description = (
    read("README.rst") + "\n" + read("CHANGES.txt") + "\n" + read("CONTRIBUTORS.txt")
)

setup(
    name="collective.sentry",
    version=version,
    description="Sentry integration with Plone 5.2/Zope 4",
    long_description=long_description,
    python_requires=">=3.9",
    # Get more strings from
    # http://www.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Framework :: Plone",
        "Framework :: Plone :: 6.0",
        "Framework :: Plone :: 6.1",
        "Framework :: Zope",
        "Framework :: Zope :: 5",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    keywords="policy",
    author="Andreas Jung",
    author_email="info@zopyx.com",
    license="GPL",
    packages=find_packages(exclude=["ez_setup"]),
    namespace_packages=[
        "collective",
    ],
    include_package_data=True,
    project_urls={
        "Code": "https://github.com/collective/collective.sentry",
        "Tracker": "https://github.com/collective/collective.sentry/issues",
    },
    zip_safe=False,
    install_requires=["setuptools", "sentry-sdk", "Zope", "plone.api"],
    entry_points="""
      # -*- Entry points -*-
      [z3c.autoinclude.plugin]
      target = plone
      """,
)
