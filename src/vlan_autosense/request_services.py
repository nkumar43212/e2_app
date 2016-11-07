#!/usr/bin/env python
#
# Copyright (c) 2016, Juniper Networks, Inc.
# All rights reserved.
#
# Author (Abbas Sakarwala - abbas@juniper.net)
#
# This module has code to send POST/PUT/GET request for services.
#

# Libraries/Modules
import os
import sys
import time
import json

sys.path.append(os.path.expanduser('../'))

import third_party.requests.requests as requests
from infra.log import Logger

# Logger
_LOG = Logger("e2_app", __name__, "debug")


SERVICE_ADD_PAYLOAD = {
    "name":"@name",
	"access_node": "@access_node",
	"access_port": "access_port",
	"access_vlans": "@vlan_list",
	"service_node": "@service_node"
}

class ServiceClient(object):
    def __init__(self, e2_web_ip, e2_web_port):
        self.e2_web_ip = e2_web_ip
        self.e2_web_port = e2_web_port

    def addNewService(self, name, access_node, access_port, vlan_list, service_node):
        payload = SERVICE_ADD_PAYLOAD.copy()
        payload["name"] = name
        payload["access_node"] = access_node
        payload["access_port"] = access_port
        payload["access_vlans"] = vlan_list
        payload["service_node"] = service_node
        request_url = "http://" + str(self.e2_web_ip) + ":" + str(self.e2_web_port) + "/services"
        try:
            r_post = requests.post(request_url, data=json.dumps(payload))
        except:
            _LOG.error("Request Exception")
            return 1
        if r_post.status_code == 200:
            _LOG.info("Request Successfully configured the service " + name)
            return 0
        else:
            _LOG.error("Request Failed with the following status: " + str(r_post.status_code))
            return 1

if __name__ == "__main__":
    # Set the logger handler - log, max, #files, format, level
    # TODO --- filename will fail in pyCharm due to complete absolute path
    filename = __file__
    filename = filename.split(".")
    filename = filename[0]
    if '/' in filename:
        filename = "request_services"
    _LOG.set_handler("/tmp/" + filename + ".log", 65535, 2, "")
    _LOG.set_level("DEBUG")

    try:
        client = ServiceClient('127.0.0.1', 10001)
        status = client.addNewService("red-customer", "vmxAbbasAccess", "ge-0/0/0", [100], "vmxAbbasService01")
    except:
        print "Some error"
