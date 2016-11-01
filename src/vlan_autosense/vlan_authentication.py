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

# VlanServiceDB
VlanServiceDB = None

class VlanDb(object):
    def __init__(self):
        pass

    def findVlanServiceObj(self, node, port, vlan):
        if VlanServiceDB == None:
            return None
        for vlanservice in VlanServiceDB:
            vlanmin = vlanservice['accessVlanMin']
            if vlanservice['accessNode'] == node and                                                \
               vlanservice['accessPort'] == port and                                                \
               (vlan >= vlanmin and vlan <= vlanservice.get('accessVlanMax', vlanmin)):
                return vlanservice

# Main function
if __name__ == "__main__":
    try:
        schema = open("vlan_service_schema.json").read()
        data = open("vlan_service_db.json").read()
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

    data_json = json.loads(data)
    VlanServiceDB = data_json["VlanServiceDB"]

    vlandb = VlanDb()
    vlan_list = [100, 200, 202, 140, 151]
    for vlan in vlan_list:
        vlanservice = vlandb.findVlanServiceObj('vmxAccess', 'ge-0/1/1', vlan)
        print vlanservice
