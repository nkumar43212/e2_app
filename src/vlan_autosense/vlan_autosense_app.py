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

sys.path.append(os.path.expanduser('../'))

import third_party.requests.requests as requests
from infra.log import Logger

# Logger
_LOG = Logger("e2_app", __name__, "debug")

# Define a function for the thread
def print_time(threadName, delay):
   count = 0
   while count < 5:
      time.sleep(delay)
      count += 1
      print "%s: %s" % (threadName, time.ctime(time.time()))

def vlan_autosense(threadName):
    pass

def upd_receive(threadName):
    UDP_IP = "127.0.0.1"
    UDP_PORT = 15000

    sock = socket.socket(socket.AF_INET,  # Internet
                         socket.SOCK_DGRAM)  # UDP
    sock.bind((UDP_IP, UDP_PORT))

    print "Ready to receive UDP data traffic on port = " + str(UDP_PORT)
    count = 0
    while True:
        data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
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
        thread.start_new_thread(print_time, ("Thread-1", 2, ))
        thread.start_new_thread(print_time, ("Thread-2", 4, ))
        thread.start_new_thread(upd_receive, ("Thread-3", ))
    except:
        print "Error: unable to start thread"

    while 1:
        pass
