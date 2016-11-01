#!/usr/bin/env python
#
# Copyright (c) 2016, Juniper Networks, Inc.
# All rights reserved.
#
# Author (Abbas Sakarwala - abbas@juniper.net)
#
# This module has CRUD implementation for service placement.
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
from infra.basicfunc import *
from network_element import _ne_dict
from conn_link import _conn_link_dict
from contrail_infra_client.mxrouter import mx_router
from contrail_infra_client.provision_mxrouters import *

# Logger
_LOG = Logger("e2_app", __name__, "debug")

# Pattern match
namepattern = re.compile(r'^[a-zA-Z\d-]{1,64}$')

# Graph
_services_dict = dict()

# Services Class
class Services(object):
    def __init__(self, name, access_node, access_port, access_vlans,
                 service_node = None):
        self.name = name
        self.access_node = access_node
        self.access_port = access_port
        self.access_vlans = access_vlans
        self.service_node = service_node

    def json(self):
        tmp_dict = dict()
        tmp_dict['name'] = self.name
        tmp_dict['access_node'] = self.access_node
        tmp_dict['access_port'] = self.access_port
        tmp_dict['access_vlans'] = self.access_vlans
        tmp_dict['service_node'] = self.service_node
        return tmp_dict

#######################################################################

@post('/services')
def services_creation_handler():
    # Handles Services creation
    _LOG.debug("POST method - /services")
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
            if data['access_port'] is None:
                _LOG.exception("Incorrect (key:access_port) value in data = " + str(data))
                raise ValueError
            access_port = data['access_port']
            if data['access_vlans'] is None:
                _LOG.exception("Incorrect (key:access_vlans) value in data = " + str(data))
                raise ValueError
            # Note access_vlans is a list of vlans
            access_vlans = data['access_vlans']
            for avlan in access_vlans:
                if ((avlan <= 0) or (avlan > 1024)):
                    _LOG.exception("Some incorrect (key:access_vlans) value in data = " + str(data))
                    raise ValueError
            if namepattern.match(data['service_node']) is None:
                _LOG.exception("Incorrect (key:service_node) value in data = " + str(data))
                raise ValueError
            service_node = data['service_node']
        except (TypeError, KeyError):
            _LOG.exception("Missing keys (name, access_node, access_port, access_vlans, service_node) in data = " +
                           str(data))
            raise ValueError

        # check for existence
        if name in _services_dict.keys():
            _LOG.exception("Name already exist " + name + " in data = " + str(data))
            raise KeyError

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

        # Check for existence - connection between access and service
        found_conn = False
        conn_link_obj = None
        for cl_obj in _conn_link_dict.itervalues():
            if cl_obj.access_node == access_node and cl_obj.service_node == service_node:
                _LOG.debug("Connection link exist between " + access_node + " and " + service_node)
                conn_link_obj = cl_obj
                found_conn = True
        if not found_conn:
            _LOG.debug("NO Connection link found between " + access_node + " and " + service_node)
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

    # Create Service object
    service_obj = Services(name, access_node, access_port, access_vlans, service_node)
    # print(json.dumps(service_obj, default=jdefault))

    # Increment service ref count
    conn_link_obj.add_ref_cnt()
    _services_dict[name] = service_obj

    # Create access physical interface
    mx_router.add_network_physical_interfaces(ne_access_obj.name, access_port)

    # Contrail service addition
    vlan_list = []
    for avlan in access_vlans:
        vlan_list.append(str(avlan))
    mx_router.addService(ne_access_obj.name, ne_access_obj.router_id+"/32",
                         access_port, conn_link_obj.access_fab_intf, vlan_list,
                         ne_service_obj.name, ne_service_obj.router_id+"/32")

    # return 200 Success
    _LOG.debug("Good, return 200 Success")
    response.headers['Content-Type'] = 'application/json'
    return json.dumps({'name': name})


@get('/services')
def services_listing_handler():
    # Handles Services listing
    _LOG.debug("GET method - /services")
    response.headers['Content-Type'] = 'application/json'
    response.headers['Cache-Control'] = 'no-cache'
    tmp_list = []
    for key, value in _services_dict.iteritems():
        # tmp_list.append(json.dumps(value, default=jdefault))
        # tmp_list.append(json.dumps(value))
        # tmp_list.append(json.dumps(value.json()))
        # tmp_list.append(value.json()) --- works well
        tmp_list.append(value.__dict__)
    _LOG.debug("Good, return 200 Success")
    return json.dumps({"services": tmp_list})


@put('/services/<name>')
def services_update_handler(name):
    # Handles Services updates
    _LOG.debug("PUT method - /services/" + name)
    try:
        # Check if name exists
        if name not in _services_dict.keys():
            _LOG.exception("Services " + name + " not present")
            raise KeyError
        service_obj = _services_dict[name]
    except KeyError:
        response.status = 404
        return

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
            if namepattern.match(data['service_node']) is None:
                _LOG.exception("Incorrect (key:service_node) value in data = " + str(data))
                raise ValueError
            new_service_node = data['service_node']
        except (TypeError, KeyError):
            _LOG.exception("Missing keys (name, service_node) in data = " +
                           str(data))
            raise ValueError

        # Get NE access node
        access_node = service_obj.access_node
        if access_node not in _ne_dict.keys():
            _LOG.exception("access_node does not exist: " + name)
            raise ValueError
        else:
            ne_access_obj = _ne_dict[access_node]
            if ne_access_obj.role != "access":
                raise ValueError

        # Get NE old service node
        old_service_node = service_obj.service_node
        if old_service_node not in _ne_dict.keys():
            _LOG.exception("old_service_node does not exist: " + name)
            raise ValueError
        else:
            old_ne_service_obj = _ne_dict[old_service_node]
            if old_ne_service_obj.role != "service":
                raise ValueError

        # Check for existence - new service node
        if new_service_node not in _ne_dict.keys():
            _LOG.exception("service_node does not exist " + name + " in _ne_dict")
            raise ValueError
        else:
            new_ne_service_obj = _ne_dict[new_service_node]
            if new_ne_service_obj.role != "service":
                raise ValueError

        # Check for existence - connection between access and new service
        found_conn = False
        new_conn_link_obj = None
        for cl_obj in _conn_link_dict.itervalues():
            if cl_obj.access_node == access_node and cl_obj.service_node == new_service_node:
                _LOG.debug("Connection link exist between " + access_node + " and " + new_service_node)
                new_conn_link_obj = cl_obj
                found_conn = True
        if not found_conn:
            _LOG.debug("NO Connection link found between " + access_node + " and " + new_service_node)
            raise ValueError

        # Check for existence - connection between access and old service
        found_conn = False
        old_conn_link_obj = None
        for cl_obj in _conn_link_dict.itervalues():
            if cl_obj.access_node == access_node and cl_obj.service_node == old_service_node:
                _LOG.debug("Connection link exist between " + access_node + " and " + old_service_node)
                old_conn_link_obj = cl_obj
                found_conn = True
        if not found_conn:
            _LOG.debug("NO Connection link found between " + access_node + " and " + old_service_node)
            raise ValueError

    except ValueError:
        response.status = 400
        return
    except KeyError as e:
        response.status = e.args[0]
        return

    # Let's configure the service now
    # Update Service object with new service node name
    service_obj.service_node = new_service_node
    # print(json.dumps(service_obj, default=jdefault))

    # Increment new service ref count
    new_conn_link_obj.add_ref_cnt()

    # Contrail new service addition
    vlan_list = []
    for avlan in service_obj.access_vlans:
        vlan_list.append(str(avlan))
    mx_router.addService(ne_access_obj.name, ne_access_obj.router_id+"/32",
                         service_obj.access_port, new_conn_link_obj.access_fab_intf, vlan_list,
                         new_ne_service_obj.name, new_ne_service_obj.router_id+"/32")

    # Contrail old service deletion
    mx_router.deleteService(ne_access_obj.name, ne_access_obj.router_id+"/32",
                            service_obj.access_port, old_conn_link_obj.access_fab_intf, vlan_list,
                            old_ne_service_obj.name, old_ne_service_obj.router_id+"/32")

    # Decrement old service ref count
    old_conn_link_obj.del_ref_cnt()

    # return 200 Success
    _LOG.debug("Good, return 200 Success")
    response.headers['Content-Type'] = 'application/json'
    return json.dumps({'name': name})


@delete('/services/<name>')
def services_delete_handler(name):
    # Handles Services deletions
    _LOG.debug("DELETE method - /services/" + name)
    try:
        # Check if name exists
        if name not in _services_dict.keys():
            _LOG.exception("Services " + name + " not present")
            raise KeyError
        service_obj = _services_dict[name]
    except KeyError:
        response.status = 404
        return
    except ValueError:
        response.status = 400
        return

    try:
        # Get all NE objects
        access_node = service_obj.access_node
        ne_access_obj = _ne_dict[access_node]

        service_node = service_obj.service_node
        ne_service_obj = _ne_dict[service_node]

        # Get conn_link obj
        found_conn = False
        conn_link_obj = None
        for cl_obj in _conn_link_dict.itervalues():
            if cl_obj.access_node == access_node and cl_obj.service_node == service_node:
                _LOG.debug("Connection link exist between " + access_node + " and " + service_node)
                conn_link_obj = cl_obj
                found_conn = True
        if not found_conn:
            _LOG.debug("NO Connection link found between " + access_node + " and " + service_node)
            raise ValueError

        # Contrail service deletion
        vlan_list = []
        for avlan in service_obj.access_vlans:
            vlan_list.append(str(avlan))
        mx_router.deleteService(ne_access_obj.name, ne_access_obj.router_id+"/32",
                                service_obj.access_port, conn_link_obj.access_fab_intf, vlan_list,
                                ne_service_obj.name, ne_service_obj.router_id+"/32")

        # Decrement service ref count
        conn_link_obj.del_ref_cnt()

        # Delete the service object as well
        del service_obj
        del _services_dict[name]

    except:
        _LOG.debug("Some thing wrong with NE object ref count decrement")
        response.status = 400
        return

    _LOG.debug("Good, return 200 Success")
    return
