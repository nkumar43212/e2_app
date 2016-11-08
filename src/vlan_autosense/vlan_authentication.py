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

# VlanConfiguredServiceDB
VlanCfgServiceDB = dict()


def initializeVlanServiceDB(schema_file, data_file):
    try:
        schema = open(schema_file).read()
        data = open(data_file).read()
        try:
            jsonschema.validate(json.loads(data), json.loads(schema))
        except jsonschema.ValidationError as e:
            print e.message
        except jsonschema.SchemaError as e:
            print e
        else:
            _LOG.info("Authentication Schema and Data is good")

    except:
        _LOG.exception("Authentication Files not found in local directory")
        sys.exit(1)

    # Intialize the DB
    data_json = json.loads(data)
    global VlanServiceDB
    VlanServiceDB = data_json["VlanServiceDB"]

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
        return None

# Same as "from request_services import SERVICE_ADD_PAYLOAD"
class VlanCfgDb(object):
    def __init__(self):
        pass

    def findVlanServiceObj(self, node, port, vlan):
        vlan_list = []
        vlan_list.append(vlan)
        for servicename, serviceobj in VlanCfgServiceDB.iteritems():
            if  serviceobj["access_node"] == node and       \
                serviceobj["access_port"] == port and       \
                serviceobj["access_vlans"] == vlan_list:
                return serviceobj
        return None

    def addVlanServiceObj(self, serviceobj):
        VlanCfgServiceDB[serviceobj["name"]] = serviceobj

    def delVlanServiceObj(self, serviceobj):
        del VlanCfgServiceDB[serviceobj["name"]]

class VlanService(object):
    def __init__(self):
        pass

    def searchAndAddService(self, access_node, access_port, access_vlan):
        vlancfgdb = VlanCfgDb()
        serviceobj = vlancfgdb.findVlanServiceObj(access_node, access_port, access_vlan)
        if serviceobj is not None:
            _LOG.info("Service for vlan already configured: (" + access_node + ", " +
                      access_port + ", "  + str(access_vlan) + ")")
            return None
        else:
            vlandb = VlanDb()
            vlanservice = vlandb.findVlanServiceObj(access_node, access_port, access_vlan)
            if vlanservice is not None:
                from request_services import SERVICE_ADD_PAYLOAD
                serviceobj = SERVICE_ADD_PAYLOAD.copy()
                vlanmin = vlanservice['accessVlanMin']
                # Set service name accordingly
                if vlanservice.get('accessVlanMax', vlanmin) == vlanmin:
                    serviceobj['name'] = vlanservice['serviceName']
                else:
                    serviceobj['name'] = vlanservice['serviceName'] + "-" + str(access_vlan)
                vlan_list = []
                vlan_list.append(access_vlan)
                serviceobj['access_node'] = access_node
                serviceobj['access_port'] = access_port
                serviceobj['access_vlans'] = vlan_list
                serviceobj['service_node'] = vlanservice['serviceNode']
                vlancfgdb.addVlanServiceObj(serviceobj)
                _LOG.info("Service for vlan found in authentication DB and Added: (" + access_node + ", " +
                          access_port + ", " + str(access_vlan) + ")")
                return serviceobj
            else:
                _LOG.info("Service for vlan not found in authentication DB: (" + access_node + ", " +
                          access_port + ", "  + str(access_vlan)  + ")")
                return None


# Main function
if __name__ == "__main__":
    # Set the logger handler - log, max, #files, format, level
    # TODO --- filename will fail in pyCharm due to complete absolute path
    filename = __file__
    filename = filename.split(".")
    filename = filename[0]
    if '/' in filename:
        filename = "vlan_authentication"
    _LOG.set_handler("/tmp/" + filename + ".log", 65535, 2, "")
    _LOG.set_level("DEBUG")

    initializeVlanServiceDB("vlan_service_schema.json", "vlan_service_db.json")

    # Within service db
    vlandb = VlanDb()
    vlan_list = [100, 200, 202, 140, 151]
    for vlan in vlan_list:
        vlanservice = vlandb.findVlanServiceObj('vmxAccess', 'ge-0/0/0', vlan)
        print vlanservice

    # Within current config db
    vlancfgdb = VlanCfgDb()
    vlancfgdb.findVlanServiceObj("vmxAccess", "ge-0/0/0", 100)

    print "\n\nVlan searching"
    vlanservice = VlanService()
    vlanservice.searchAndAddService("vmxAccess", "ge-0/0/0", 100)
    vlanservice.searchAndAddService("vmxAccess", "ge-0/0/0", 100)
