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
import re
import json
import socket
from collections import OrderedDict

sys.path.append(os.path.expanduser('../'))

from bottle import request, response, post, get, put, delete
from infra.log import Logger
from network_element import _ne_dict
from contrail_infra_client.mxrouter import mx_router
from contrail_infra_client.provision_mxrouters import *

# Logger
_LOG = Logger("e2_app", __name__, "debug")

# Pattern match
namepattern = re.compile(r'^[a-zA-Z\d-]{1,64}$')

# Graph
_conn_link_dict = dict()

# Conn Link Class
class ConnLink(object):
    def __init__(self, name, access_node, access_links,
                 service_node, service_links, fabric = None):
        self.name = name
        self.access_node = access_node
        self.service_node = service_node
        self.access_links = access_links
        self.service_links = service_links
        self.fabric = fabric
        self.access_fab_intf = None
        self.service_fab_intf = None
        self.ref_cnt = 0

    def json(self):
        tmp_dict = dict()
        tmp_dict['name'] = self.name
        tmp_dict['access_node'] = self.access_node
        tmp_dict['service_node'] = self.service_node
        tmp_dict['access_links'] = self.access_links
        tmp_dict['service_links'] = self.service_links
        tmp_dict['fabric'] = self.fabric
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
            if namepattern.match(data['access_node']) is None:
                _LOG.exception("Incorrect (key:access_node) value in data = " + str(data))
                raise ValueError
            access_node = data['access_node']
            if namepattern.match(data['service_node']) is None:
                _LOG.exception("Incorrect (key:service_node) value in data = " + str(data))
                raise ValueError
            service_node = data['service_node']
            if data['fabric'] is not None:
                _LOG.exception("Incorrect (key:fabric) value in data = " + str(data))
                raise ValueError
            fabric = data['fabric']
            if data['access_links'] is None:
                _LOG.exception("Incorrect (key:access_links) value in data = " + str(data))
                raise ValueError
            access_links = data['access_links']
            if data['service_links'] is None:
                _LOG.exception("Incorrect (key:service_links) value in data = " + str(data))
                raise ValueError
            service_links = data['service_links']
        except (TypeError, KeyError):
            _LOG.exception("Missing keys (name, access_node, access_links, service_node, service_links, fabric) "
                           "in data = " + str(data))
            raise ValueError

        # check for existence
        if name in _conn_link_dict.keys():
            _LOG.exception("Name already exist " + name + " in data = " + str(data))
            raise KeyError

        # Check length
        if (len(access_links) != len(service_links)) or (len(access_links) == 0):
            _LOG.exception("Incorrect access_links and service_links value in data = " + str(data))
            raise ValueError

        # Check for existence - access node
        if access_node not in _ne_dict.keys():
            _LOG.exception("access_node does not exist " + name + " in data = " + str(data))
            raise ValueError
        else:
            ne_access_obj = _ne_dict[access_node]
            if ne_access_obj.role != "access":
                raise ValueError

        # Check for existence - service node
        if service_node not in _ne_dict.keys():
            _LOG.exception("service_node does not exist " + name + " in data = " + str(data))
            raise ValueError
        else:
            ne_service_obj = _ne_dict[service_node]
            if ne_service_obj.role != "service":
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
    conn_link_obj = ConnLink(name, access_node, access_links, service_node, service_links, fabric)
    # print(json.dumps(conn_link_obj, default=jdefault))

    # Increment ref count of each NE objects
    access_node_obj = _ne_dict[access_node]
    access_node_obj.add_ref_cnt()
    service_node_obj = _ne_dict[service_node]
    service_node_obj.add_ref_cnt()
    _conn_link_dict[name] = conn_link_obj

    # Contrail link addition
    # Add access node interfaces
    for intf in conn_link_obj.access_links:
        print "access: " + intf
        mx_router.add_network_physical_interfaces(access_node_obj.name, access_node_obj.mgmt_ip, intf)
    # Add service node interfaces
    for intf in conn_link_obj.service_links:
        print "service: " + intf
        mx_router.add_network_physical_interfaces(service_node_obj.name, service_node_obj.mgmt_ip, intf)

    # Create Fabric interface - access node
    fi_access = mx_router.create_fabric_interface(access_node_obj.name, access_node_obj.mgmt_ip)
    conn_link_obj.access_fab_intf = fi_access
    mx_router.add_child_intefaces_to_fabric(access_node_obj.name, access_node_obj.mgmt_ip,
                                            fi_access, conn_link_obj.access_links)

    # Create Fabric interface - service node
    fi_service = mx_router.create_fabric_interface(service_node_obj.name, service_node_obj.mgmt_ip)
    conn_link_obj.service_fab_intf = fi_service
    mx_router.add_child_intefaces_to_fabric(service_node_obj.name, service_node_obj.mgmt_ip,
                                            fi_service, conn_link_obj.service_links)

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
        if conn_link_obj.ref_cnt != 0:
            _LOG.debug("Conn Link " + name + " still referenced")
            raise ValueError
    except KeyError:
        response.status = 404
        return
    except ValueError:
        response.status = 400
        return

    # Decrement ref count of each NE objects
    try:
        access_node = conn_link_obj.access_node
        access_node_obj = _ne_dict[access_node]
        access_node_obj.del_ref_cnt()

        service_node = conn_link_obj.service_node
        service_node_obj = _ne_dict[service_node]
        service_node_obj.del_ref_cnt()
    except:
        _LOG.debug("Some thing wrong with NE object ref count decrement")
        response.status = 400
        return

    # Contrail link removal
    # Delete Fabric interface - access node
    mx_router.del_child_intefaces_from_fabric(access_node_obj.name, access_node_obj.mgmt_ip,            \
                                              conn_link_obj.access_fab_intf, conn_link_obj.access_links)
    mx_router.delete_fabric_interface(access_node_obj.name, access_node_obj.mgmt_ip, conn_link_obj.access_fab_intf)

    # Delete Fabric interface - service node
    mx_router.del_child_intefaces_from_fabric(service_node_obj.name, service_node_obj.mgmt_ip,          \
                                              conn_link_obj.service_fab_intf, conn_link_obj.service_links)
    mx_router.delete_fabric_interface(service_node_obj.name, service_node_obj.mgmt_ip, conn_link_obj.service_fab_intf)

    # Delete access node interfaces
    for intf in conn_link_obj.access_links:
        print "access: " + intf
        mx_router.del_network_physical_interfaces(access_node_obj.name, access_node_obj.mgmt_ip, intf)
    # Delete service node interfaces
    for intf in conn_link_obj.service_links:
        print "service: " + intf
        mx_router.del_network_physical_interfaces(service_node_obj.name, service_node_obj.mgmt_ip, intf)

    # Delete the conn_link object as well
    del conn_link_obj
    del _conn_link_dict[name]

    _LOG.debug("Good, return 200 Success")
    return
