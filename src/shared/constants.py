#!/usr/bin/env python
#
# Copyright (c) 2016, Juniper Networks, Inc.
# All rights reserved.
#
# Author (Abbas Sakarwala - abbas@juniper.net)
#
# This module defines the E2 constants used
#

# Libraries/Modules
import struct

class ROClass(type):
    def __setattr__(self, name, value):
        raise ValueError("Cannot modify %s" % name)

class E2Constants(object):

    """
    This class exists only so that we can define all the E2 constants 
    in one place.

    It is not meant to be instantiated and will raise an exception if
    an attempt is made to do so.
    """
    # Make sure nobody is able to modify a constant
    __metaclass__ = ROClass

    PIDFILE = '/var/run/e2_app.pid'
    VERSION = 1.0

    # E2_App IP and Port
    HOST = '0.0.0.0'
    HTTP_PORT = 10001

    # E2 mode
    MODE_ADJ_API = 'Adj_Api'
    MODE_ADJ_DISCOVER = 'Adj_Discover'
    MODE = set([MODE_ADJ_API, MODE_ADJ_DISCOVER])

    # Error codes
    SUCCESS = 0
    FAIL = 1

    # Make sure that this cannot be instantiated
    def __new__(cls, *args, **kwargs):
        raise TypeError("Cannot be instantiated")


# Main function
if __name__ == "__main__":
    # print E2Constants.__dict__

    print E2Constants.HOST
    print E2Constants.HTTP_PORT
    print E2Constants.MODE
    print E2Constants.MODE_ADJ_API
    print E2Constants.MODE_ADJ_DISCOVER
    print E2Constants.VERSION
    print E2Constants.SUCCESS
    print E2Constants.FAIL
    print E2Constants.PIDFILE
