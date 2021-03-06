"""
An implementation of JSON Schema for Python

The main functionality is provided by the validator classes for each of the
supported JSON Schema versions.

Most commonly, :func:`validate` is the quickest way to simply validate a given
instance under a schema, and will create a validator for you.

"""

from jsonschema.exceptions import (
    ErrorTree, FormatError, RefResolutionError, SchemaError, ValidationError
)
from jsonschema._format import (
    FormatChecker, draft3_format_checker, draft4_format_checker,
)
from jsonschema.validators import (
    Draft3Validator, Draft4Validator, RefResolver, validate
)

# from jsonschema._version import __version__
__version__ = '2.5.1'
__sha__ = 'g3f459b7'
__revision__ = 'g3f459b7'

# flake8: noqa
