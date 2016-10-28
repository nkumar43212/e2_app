#!/usr/bin/env python
#
# Copyright (c) 2016, Juniper Networks, Inc.
# All rights reserved.
#
# Author (Abbas Sakarwala - abbas@juniper.net)
#
# This module initializes bottle framework.
#

# Libraries/Modules
import os
import sys
sys.path.append(os.path.expanduser('../'))

import bottle
import network_element
import conn_link
import services
from infra.log import Logger

# Logger
_LOG = Logger("e2_app", __name__, "debug")

def web_rest_api (host, port, mode):
    # Start the webserver for REST api
    _LOG.debug("Starting E2 Application on port " + str(port))
    bottle.run(host=host, port=port, debug=True)

# Main function
if __name__ == "__main__":
    # Logging
    _LOG = Logger("e2_app", __name__, "debug")

    # Set the logger handler - log, max, #files, format, level
    filename = os.path.basename(__file__)
    filename = filename.split(".")
    filename = filename[0]
    _LOG.set_handler("/tmp/" + filename + ".log", 65535, 2, "")
    _LOG.set_level("debug")

    from shared.constants import E2Constants as e2consts
    web_rest_api('0.0.0.0', 10001, e2consts.MODE_ADJ_API)
