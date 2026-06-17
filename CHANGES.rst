1.0.0 (2026-06-17)
------------------

Breaking changes:


- Drop support for Plone 5.2 and Python 3.8. (#28)
- Replace ``pkg_resources`` namespace with PEP 420 native namespace.
  Support only Plone 6.2 and Python 3.10+. (#3928)


Bug fixes:


- Handle non exceptions that caused a traceback @gforcada (#29)


Internal:


- Update configuration files.
  Move to src-layout.
  [plone devs]
