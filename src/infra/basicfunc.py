#!/usr/bin/env python
#
# Copyright (c) 2016, Juniper Networks, Inc.
# All rights reserved.
#
# Author (Abbas Sakarwala - abbas@juniper.net)
#
# This module defines some basic util functions
#

# Libraries/Modules
import json
import socket

# Util function
def valid_ip(address):
    try:
        socket.inet_aton(address)
        return True
    except:
        return False

# Json convertor
def jdefault(o):
    if isinstance(o, set):
        return list(o)
    return o.__dict__
