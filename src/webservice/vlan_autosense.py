#!/usr/bin/env python
#
# Copyright (c) 2016, Juniper Networks, Inc.
# All rights reserved.
#
# Author (Abbas Sakarwala - abbas@juniper.net)
#
# This module has CRUD implementation for vlan-autosense-port.
#

# Libraries/Modules
import os
import sys

sys.path.append(os.path.expanduser('../'))

import re
import json
from infra.basicfunc import *
from collections import OrderedDict
from bottle import request, response, post, get, put, delete
import infra.id_manager as id_manager
from infra.log import Logger

from network_element import _ne_dict
from contrail_infra_client.mxrouter import mx_router
from contrail_infra_client.provision_mxrouters import *

# Logger
_LOG = Logger("e2_app", __name__, "debug")

# Dict of Vlan Autosense port (key=name, value=port)
_vlan_autosense = dict()

# Pattern match
namepattern = re.compile(r'^[a-zA-Z\d-]{1,64}$')

# Role types
role_types = ["access", "service"]

#######################################################################

@post('/vlan-autosense')
def vlanauto_creation_handler():
    # Handles Vlan Autosense creation
    _LOG.debug("POST method - /vlan-autosense")
    try:
        # parse input data
        try:
            # Convert to json
            body_data = request.body.read()
            data = json.loads(body_data, object_pairs_hook=OrderedDict)
            # data = request.json() --- not working
        except:
            _LOG.exception("Data value provided has errors = " + body_data)
            raise ValueError

        if data is None:
            _LOG.exception("Data value is None")
            raise ValueError

        # extract and validate
        try:
            if namepattern.match(data['access_node']) is None:
                _LOG.exception("Incorrect (key:access_node) value in data = " + str(data))
                raise ValueError
            access_node = data['access_node']
            if data['port'] is None:
                _LOG.exception("Incorrect (key:port) value in data = " + str(data))
                raise ValueError
            port = data['port']
        except (TypeError, KeyError):
            _LOG.exception("Missing keys (access_node, port) in data = " + str(data))
            raise ValueError

        # check for existence
        if (access_node, port) in _vlan_autosense.keys():
            _LOG.exception("Name already exist (" + access_node + ", " + port + ") in _vlan_autosense")
            raise KeyError

        # Check for existence - access node
        if access_node not in _ne_dict.keys():
            _LOG.exception("access_node does not exist " + access_node + " in _ne_dict")
            raise ValueError
        else:
            ne_access_obj = _ne_dict[access_node]
            if ne_access_obj.role != "access":
                _LOG.exception("Not an access_node " + access_node + " in _ne_dict")
                raise ValueError

    except ValueError:
        # if bad request data, return 400 Bad Request
        _LOG.debug("Bad request data, return 400 Bad Request")
        response.status = 400
        return

    except KeyError:
        # if name already exists, return 409 Conflict
        _LOG.debug("Name already exists, return 409 Conflict")
        response.status = 409
        return

    # Add in dict
    _vlan_autosense[(access_node, port)] = None

    # Add in contrail
    mx_router.add_network_physical_interfaces(access_node, port)

    # return 200 Success
    _LOG.debug("Good, return 200 Success")
    response.headers['Content-Type'] = 'application/json'
    return json.dumps({'access_node': access_node, 'port': port})


@get('/vlan-autosense')
def vlanauto_listing_handler():
    # Handles Vlan Autosense listing
    _LOG.debug("GET method - /vlan-autosense")
    response.headers['Content-Type'] = 'application/json'
    response.headers['Cache-Control'] = 'no-cache'
    tmp_list = []
    for key, value in _vlan_autosense.iteritems():
        # tmp_list.append(json.dumps(value, default=jdefault))
        # tmp_list.append(json.dumps(value))
        # tmp_list.append(json.dumps(value.json()))
        # tmp_list.append(value.json()) --- works well
        tmp_list.append({'access_node': key[0], 'port': key[1]})
    _LOG.debug("Good, return 200 Success")
    return json.dumps({"vlan-autosense": tmp_list})
    # return json.dumps({'names': list(_vlan_autosense_names)})


'''
@put('/vlan-autosense/<oldname>')
def vlanauto_update_handler(name):
'''


@delete('/vlan-autosense/<access_node>/<port>')
def vlanauto_delete_handler(access_node, port):
    # Handles Vlan Autosense deletions
    _LOG.debug("DELETE method - /vlan-autosense/" + access_node + "/" + port)
    try:
        # Check if access_node exists
        if (access_node, port) not in _vlan_autosense.keys():
            _LOG.exception("Name not present (" + access_node + ", " + port + ") in _vlan_autosense")
            raise KeyError
    except KeyError:
        response.status = 404
        return
    except ValueError:
        response.status = 400
        return

    # Delete
    mx_router.delete_network_physical_interfaces(name, port)

    # Delete the network element object as well
    del _vlan_autosense[(access_node, port)]

    _LOG.debug("Good, return 200 Success")
    return
