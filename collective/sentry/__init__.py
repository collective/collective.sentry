"""Main product initializer
"""

# Define a message factory for when this product is internationalised.
# This will be imported with the special name "_" in most modules. Strings
# like _(u"message") will then be extracted by i18n tools for translation.

import os
from zope.i18nmessageid import MessageFactory
MessageFactory = MessageFactory('ugent.policy')


if not os.path.exists(os.path.expanduser('~/.ugent.ldap.ini')):
    raise RuntimeError('~/.ugent.ldap.ini does not exist')


def initialize(context):
    """Initializer called when used as a Zope 2 product.

    This is referenced from configure.zcml. Registrations as a "Zope 2 product"
    is necessary for GenericSetup profiles to work, for example.

    Here, we call the Archetypes machinery to register our content types
    with Zope and the CMF.
    """

import ugent.policy.patches


import warnings
warnings.simplefilter("ignore", category=DeprecationWarning)
