#!/usr/bin/env python
#
# Copyright (c) 2016, Juniper Networks, Inc.
# All rights reserved.
#
# Author (Abbas Sakarwala - abbas@juniper.net)
#
# This module has CRUD implementation for conn-link.
#

# Libraries/Modules
import os
import sys
sys.path.append(os.path.expanduser('../'))

import re
import json
import socket
from collections import OrderedDict
from bottle import request, response, post, get, put, delete
from infra.log import Logger
from network_element import _ne_dict
from contrail_infra_client.provision_mxrouters import *

# Logger
_LOG = Logger("e2_app", __name__, "debug")

# Pattern match
namepattern = re.compile(r'^[a-zA-Z\d-]{1,64}$')

# Graph
_conn_link_dict = dict()

# Conn Link Class
class ConnLink(object):
    def __init__(self, name, left_node, left_links,
                 right_node, right_links, fabric = None):
        self.name = name
        self.left_node = left_node
        self.right_node = right_node
        self.left_links = left_links
        self.right_links = right_links
        self.fabric = fabric

    def json(self):
        tmp_dict = dict()
        tmp_dict['name'] = self.name
        tmp_dict['left_node'] = self.left_node
        tmp_dict['right_node'] = self.right_node
        tmp_dict['left_links'] = self.left_links
        tmp_dict['right_links'] = self.right_links
        tmp_dict['fabric'] = self.fabric
        return tmp_dict

#######################################################################

@post('/conn-links')
def conn_link_creation_handler():
    # Handles Conn Link creation
    _LOG.debug("POST method - /conn-links")
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
            if namepattern.match(data['left_node']) is None:
                _LOG.exception("Incorrect (key:left_node) value in data = " + str(data))
                raise ValueError
            left_node = data['left_node']
            if namepattern.match(data['right_node']) is None:
                _LOG.exception("Incorrect (key:right_node) value in data = " + str(data))
                raise ValueError
            right_node = data['right_node']
            if data['fabric'] is not None:
                _LOG.exception("Incorrect (key:fabric) value in data = " + str(data))
                raise ValueError
            fabric = data['fabric']
            if data['left_links'] is None:
                _LOG.exception("Incorrect (key:left_links) value in data = " + str(data))
                raise ValueError
            left_links = data['left_links']
            if data['right_links'] is None:
                _LOG.exception("Incorrect (key:right_links) value in data = " + str(data))
                raise ValueError
            right_links = data['right_links']
        except (TypeError, KeyError):
            _LOG.exception("Missing keys (name, left_node, left_links, right_node, right_links, fabric) in data = " +
                           str(data))
            raise ValueError

        # check for existence
        if name in _conn_link_dict.keys():
            _LOG.exception("Name already exist " + name + " in data = " + str(data))
            raise KeyError

        # Check length
        if (len(left_links) != len(right_links)) or (len(left_links) == 0):
            _LOG.exception("Incorrect left_links and right_links value in data = " + str(data))
            raise ValueError

        # Check for existence - left node
        if left_node not in _ne_dict.keys():
            _LOG.exception("left_node does not exist " + name + " in data = " + str(data))
            raise ValueError
        else:
            ne_left_obj = _ne_dict[left_node]
            if ne_left_obj.role != "access":
                raise ValueError

        # Check for existence - right node
        if right_node not in _ne_dict.keys():
            _LOG.exception("right_node does not exist " + name + " in data = " + str(data))
            raise ValueError
        else:
            ne_right_obj = _ne_dict[right_node]
            if ne_right_obj.role != "service":
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

    # Create Conn Link object
    conn_link_obj = ConnLink(name, left_node, left_links, right_node, right_links, fabric)
    # print(json.dumps(conn_link_obj, default=jdefault))

    # Increment ref counts
    left_node_obj = _ne_dict[left_node]
    left_node_obj.add_ref_cnt()
    right_node_obj = _ne_dict[right_node]
    right_node_obj.add_ref_cnt()
    _conn_link_dict[name] = conn_link_obj

    # Contrail link addition - TODO
    mx_router = MxRouter(' ')
    # Add left node interfaces
    for intf in conn_link_obj.left_links:
        print "left: " + intf
        mx_router.add_network_physical_interfaces(left_node_obj.name, left_node_obj.mgmt_ip, intf)
    # Add right node interfaces
    for intf in conn_link_obj.right_links:
        print "right: " + intf
        mx_router.add_network_physical_interfaces(right_node_obj.name, right_node_obj.mgmt_ip, intf)
    # fi_left = mx_router.create_fabric_interface(left_node_obj.name)
    # for intf in conn_link_obj.left_links:
    #     fi_left.add_interface(intf)
    # fi_right = mx_router.create_fabric_interface(right_node_obj.name)
    # for intf in conn_link_obj.right_links:
    #     fi_right.add_interface(intf)
    # mx_router.create_fabric_link(fi_left, fi_right)

    # return 200 Success
    _LOG.debug("Good, return 200 Success")
    response.headers['Content-Type'] = 'application/json'
    return json.dumps({'name': name})


@get('/conn-links')
def conn_link_listing_handler():
    # Handles Conn Link listing
    _LOG.debug("GET method - /conn-links")
    response.headers['Content-Type'] = 'application/json'
    response.headers['Cache-Control'] = 'no-cache'
    tmp_list = []
    for key, value in _conn_link_dict.iteritems():
        # tmp_list.append(json.dumps(value, default=jdefault))
        # tmp_list.append(json.dumps(value))
        # tmp_list.append(json.dumps(value.json()))
        # tmp_list.append(value.json()) --- works well
        tmp_list.append(value.__dict__)
    _LOG.debug("Good, return 200 Success")
    return json.dumps({"conn-links": tmp_list})


'''
@put('/conn-links/<oldname>')
def conn_link_update_handler(name):
'''


@delete('/conn-links/<name>')
def conn_link_delete_handler(name):
    # Handles Conn Link deletions
    _LOG.debug("DELETE method - /conn-links/" + name)
    try:
        # Check if name exists
        if name not in _conn_link_dict.keys():
            _LOG.exception("Conn Link " + name + " not present")
            raise KeyError
        conn_link_obj = _conn_link_dict[name]
    except KeyError:
        response.status = 404
        return
    except ValueError:
        response.status = 400
        return

    # Delete the ref count of each NE object
    try:
        _ne_dict[conn_link_obj.left_node].del_ref_cnt()
        _ne_dict[conn_link_obj.right_node].del_ref_cnt()
    except:
        _LOG.debug("Some thing wrong with NE object ref count decrement")
        response.status = 400
        return

    # Contrail link removal - TODO

    # Delete the conn_link object as well
    del conn_link_obj

    _LOG.debug("Good, return 200 Success")
    return
