#!/usr/bin/env python
#
# Copyright (c) 2016, Juniper Networks, Inc.
# All rights reserved.
#
# Author (Abbas Sakarwala - abbas@juniper.net)
#
# This module has vlan autosensing logic
#

# Libraries/Modules
import os
import sys
import thread
import time
import socket
import json
import struct

sys.path.append(os.path.expanduser('../'))

import third_party.jsonschema as jsonschema
import third_party.requests.requests as requests
from infra.log import Logger
from vlan_authentication import *
from request_services import *

# Logger
_LOG = Logger("e2_app", __name__, "debug")

def vlan_autosense_app (host, port, e2_web_ip, e2_web_port):
    # Start the vlan autosense thread
    _LOG.debug("Starting E2 Vlan Autosensing Application on port " + str(port))
    thread.start_new_thread(vlan_autosense, ("Vlan autosense thread", host, port, e2_web_ip, e2_web_port))

def vlan_autosense(threadName, host, port, e2_web_ip, e2_web_port):
    initializeVlanServiceDB("vlan_autosense/vlan_service_schema.json", "vlan_autosense/vlan_service_db.json")

    # Create socket --- TODO handle error condition
    sock = socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_DGRAM)  # UDP
    sock.bind((host, port))

    _LOG.info("Ready to receive UDP data traffic on port = " + str(port))
    count = 0
    while True:
        data, addr = sock.recvfrom(2048)  # buffer size is 2048 bytes
        count += 1
        print "Received message (", count, "): ", data

        # Decode the packet
        # TODO
        payload_len = len(data)
        print payload_len
        adj_payload_len = payload_len - 2 # size of vlan id
        vlan_data = data[0:2]
        port_data = data[2:payload_len]
        print vlan_data, port_data
        (vlan, ) = struct.unpack('!h', vlan_data)
        print "final: ", vlan
        (port, ) = struct.unpack(str(adj_payload_len) + 's', port_data)
        print port
        print type(port)
        index = port.find('\x00')
        print index
        port = port[0:index]
        print "final: ", port
        # vlan = 100
        # port = 'ge-0/0/9'
        node = 'vmxAccess'

        vlanservice = VlanService()
        serviceobj = vlanservice.searchAndAddService(node, port, vlan)

        if serviceobj is not None:
            client = ServiceClient('127.0.0.1', 10001)
            vlan_list = []
            vlan_list.append(vlan)
            status = client.addNewService(serviceobj['name'], node, port, vlan_list, serviceobj['service_node'])

# Define a function for the thread
def print_time(threadName, delay):
   count = 0
   while count < 5:
      time.sleep(delay)
      count += 1
      print "%s: %s" % (threadName, time.ctime(time.time()))


def udp_receive(threadName):
    UDP_IP = "127.0.0.1"
    UDP_PORT = 15000

    sock = socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_DGRAM)  # UDP
    sock.bind((UDP_IP, UDP_PORT))

    print "Ready to receive UDP data traffic on port = " + str(UDP_PORT)
    count = 0
    while True:
        data, addr = sock.recvfrom(2048)  # buffer size is 2048 bytes
        print "received message:", data
        count += 1

        # Do some post and get operation based on this
        r_get = requests.get("http://localhost:10001/network-elements")
        print r_get.status_code
        print r_get.text
        print r_get.json()
        payload = { "name":"vmxAccess"+str(count), "mgmt_ip": "169.254.0.20", "role": "access" }
        r_post = requests.post("http://localhost:10001/network-elements", data=json.dumps(payload))
        print r_post.status_code
        print r_post.text
        print r_post.json()

# Main function
if __name__ == "__main__":
    # Create two threads
    try:
        thread.start_new_thread(print_time, ("Thread-Timer-1", 2, ))
        thread.start_new_thread(print_time, ("Thread-Timer-2", 4, ))
        thread.start_new_thread(udp_receive, ("Thread-UDP-Receive-3", ))
    except:
        print "Error: unable to start thread"

    while 1:
        pass
