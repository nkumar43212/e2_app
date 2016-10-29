#!/usr/bin/env python
#
# Copyright (c) 2016, Juniper Networks, Inc.
# All rights reserved.
#
# Author (Abbas Sakarwala - abbas@juniper.net)
#
# This module has vlan authentication and service db and APIs
#

# Libraries/Modules
import os
import sys
import time
import json

sys.path.append(os.path.expanduser('../'))

import third_party.jsonschema as jsonschema
from infra.log import Logger

# Logger
_LOG = Logger("e2_app", __name__, "debug")

# Main function
if __name__ == "__main__":
    try:
        schema = open("vlan_service_schema.json").read()
        print schema
        data = open("vlan_service_db.json").read()
        print data
        try:
            jsonschema.validate(json.loads(data), json.loads(schema))
        except jsonschema.ValidationError as e:
            print e.message
        except jsonschema.SchemaError as e:
            print e
        else:
            print "Schema and data is good"

    except:
        print "Files not found in local directory"
