#!/usr/bin/env python
#
# Copyright (c) 2016, Juniper Networks, Inc.
# All rights reserved.
#
# Author (Abbas Sakarwala - abbas@juniper.net)
#
# This module is main routine for Elastic Edge Application.
#

# Libraries/Modules
import sys
from webservice.web_rest_api import web_rest_api
from infra.log import RootLogger
from shared.config_handler import E2ConfigHandler

# Logger
_LOG = RootLogger("e2_app", "info")

# Define E2StartupException
class E2StartupException(Exception):
    """
    E2 startup exception class
    """
    def __init__(self, data):
        self.data = data

    def __str__(self):
        return repr(self.data)

# Main function
if __name__ == "__main__":
    try:
        # Check for supported platforms
        if sys.platform.startswith('linux'):
            pass
        elif sys.platform.startswith('darwin'):
            pass
        else:
            raise E2StartupException("Platform %s not supported."%sys.platform)

        # Check for supported python version
        if sys.version_info < (2, 7, 0):
           raise E2StartupException("Python version < 2.7 not supported")

        # Create E2ConfigHandler object to parse config file and input arguments
        config_handler = E2ConfigHandler()
        config_handler.options_handle()

        # Changing log handler and set level
        _LOG.set_handler(config_handler.e2_cfg.log_file_path + "/" + config_handler.e2_cfg.log_file_name,
                         5242880, 5)
        _LOG.set_level(config_handler.e2_cfg.log_level)

        # Start the web service
        web_rest_api(config_handler.e2_cfg.host, config_handler.e2_cfg.http_port, config_handler.e2_cfg.mode)

    except E2StartupException as e:
        sys.exit("Startup exception: " + str(e))
