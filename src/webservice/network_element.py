#!/usr/bin/env python
#
# Copyright (c) 2016, Juniper Networks, Inc.
# All rights reserved.
#
# Author (Abbas Sakarwala - abbas@juniper.net)
#
# This module has CRUD implementation for network-element.
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
from infra.log import Logger
from contrail_infra_client.provision_mxrouters import *

# Logger
_LOG = Logger("e2_app", __name__, "debug")

# Dict of NE (key=name, value=NE obj)
_ne_dict = dict()

# Pattern match
namepattern = re.compile(r'^[a-zA-Z\d-]{1,64}$')
ippattern = re.compile("\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}")

# Role types
role_types = ["access", "service"]

# Network Element Class
class NetworkElement(object):
    def __init__(self, name, mgmt_ip, role,
                 username='root', password='Embe1mpls'):
        self.name = name
        self.mgmt_ip = mgmt_ip
        self.role = role
        self.username = username
        self.password = password
        self.ref_cnt = 0

    def json(self):
        tmp_dict = dict()
        tmp_dict['name'] = self.name
        tmp_dict['mgmt_ip'] = self.mgmt_ip
        return tmp_dict

    def add_ref_cnt(self):
        self.ref_cnt += 1

    def del_ref_cnt(self):
        try:
            if self.ref_cnt == 0:
                raise Exception
            else:
                self.ref_cnt -= 1
        except:
            _LOG.exception("Cannot decrement zero value ref_cnt")

#######################################################################

@post('/network-elements')
def ne_creation_handler():
    # Handles NE creation
    _LOG.debug("POST method - /network-elements")
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
            if namepattern.match(data['name']) is None:
                _LOG.exception("Incorrect (key:name) value in data = " + str(data))
                raise ValueError
            name = data['name']
            if ippattern.match(data['mgmt_ip']) is None:
                _LOG.exception("Incorrect (key:mgmt_ip) value in data = " + str(data))
                raise ValueError
            mgmt_ip = data['mgmt_ip']
            if not valid_ip(mgmt_ip):
                _LOG.exception("Invalid ip address (key:mgmt_ip) value in data = " + mgmt_ip)
                raise ValueError
            if data['role'] not in role_types:
                _LOG.exception("Incorrect (key:role) value in data = " + str(data))
                raise ValueError
            role = data['role']
        except (TypeError, KeyError):
            _LOG.exception("Missing keys (name, mgmt_ip, role) in data = " + str(data))
            raise ValueError

        # check for existence
        if name in _ne_dict.keys():
            raise KeyError

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

    # Create NE object
    ne_obj = NetworkElement(name, mgmt_ip, role)
    # print(json.dumps(ne_obj, default=jdefault))
    _ne_dict[name] = ne_obj

    # Create in Contrail --- TODO REVISIT --- Check for error condition as well
    mx_router = MxRouter(' ')
    mx_router.add_network_element(name, mgmt_ip)

    # return 200 Success
    _LOG.debug("Good, return 200 Success")
    response.headers['Content-Type'] = 'application/json'
    return json.dumps({'name': name})

@get('/network-elements')
def ne_listing_handler():
    # Handles NE listing
    _LOG.debug("GET method - /network-elements")
    response.headers['Content-Type'] = 'application/json'
    response.headers['Cache-Control'] = 'no-cache'
    tmp_list=[]
    for key, value in _ne_dict.iteritems():
        # tmp_list.append(json.dumps(value, default=jdefault))
        # tmp_list.append(json.dumps(value))
        # tmp_list.append(json.dumps(value.json()))
        # tmp_list.append(value.json()) --- works well
        tmp_list.append(value.__dict__)
    _LOG.debug("Good, return 200 Success")
    return json.dumps({"network-elements":tmp_list})
    # return json.dumps({'names': list(_network_element_names)})

'''
@put('/network-elements/<oldname>')
def ne_update_handler(name):
'''

@delete('/network-elements/<name>')
def ne_delete_handler(name):
    # Handles NE deletions
    _LOG.debug("DELETE method - /network-elements/" + name)
    try:
        # Check if name exists
        if name not in _ne_dict.keys():
            _LOG.exception("Network element " + name + " not present")
            raise KeyError
        ne_obj = _ne_dict[name]
        if ne_obj.ref_cnt != 0:
            _LOG.debug("Network Element " + name + " still referenced")
            raise ValueError
    except KeyError:
        response.status = 404
        return
    except ValueError:
        response.status = 400
        return

    # Delete in Contrail --- TODO REVISIT --- Check for error condition as well
    mx_router = MxRouter(' ')
    mx_router.delete_network_element(name)

    # Delete the network element object as well
    del _ne_dict[name]

    _LOG.debug("Good, return 200 Success")
    return
