#!/usr/bin/env python
#
# Copyright (c) 2016, Juniper Networks, Inc.
# All rights reserved.
#
# Author (Abbas Sakarwala - abbas@juniper.net)
#
# This module defines the E2 configuration object
#

# Libraries/Modules
from constants import E2Constants as e2consts

class E2Config(object):
    def __init__(self):
        # Internal config variables
        self.pidfile = e2consts.PIDFILE
        self.version = e2consts.VERSION

        # E2 mode
        self.mode = e2consts.MODE_ADJ_API

        # The interface that E2 listens to web server (rest APIs)
        self.host = e2consts.HOST

        # The port that E2 listens on to web server (rest APIs).
        self.http_port = e2consts.HTTP_PORT

        '''
        LOG files
        '''
        # TODO --- define in e2consts
        self.log_file_path = '/tmp'             # Log file path
        self.log_file_name = 'e2_app.log'       # Log file name
        self.log_level = 'INFO'                 # Log level
        self.log_file_num_backup = 10           # Number of backup log files
        self.log_file_max = 5242880             # Maximum size to which a log file can grow = 5 MB

    def __str__(self):
        str = ""
        str += ("pidfile=%s\n" % self.pidfile)
        str += ("version=%s\n" % self.version)
        str += ("mode=%s\n" % self.mode)
        str += ("host=%s\n" % self.host)
        str += ("http_port=%s\n" % self.http_port)
        str += ("log_file_path=%s\n" % self.log_file_path)
        str += ("log_file_name=%s\n" % self.log_file_name)
        str += ("log_level=%s\n" % self.log_level)
        str += ("log_file_num_backup=%s\n" % self.log_file_num_backup)
        str += ("log_file_max=%s\n" % self.log_file_max)

        return str


if __name__ == "__main__":
    import os
    import sys
    sys.path.append(os.path.expanduser('../'))
    from infra.log import Logger

    # Logging
    _LOG = Logger("E2ConfigTest", __name__, "debug")

    # Set the logger handler - log, max, #files, format, level
    filename = os.path.basename(__file__)
    filename = filename.split(".")
    filename = filename[0]
    _LOG.set_handler("/tmp/" + filename + ".log", 65535, 2, "")
    _LOG.set_level("DEBUG")

    # Initialize E2 Config
    e2config = E2Config()
    _LOG.debug("%s"%e2config)

    # Test 1 - Assign E2 mode value in E2 Config
    e2config.mode = e2consts.MODE_ADJ_DISCOVER
    if e2config.mode in e2consts.MODE:
        _LOG.debug('E2 mode check succeeded ')
    else:
        _LOG.debug('E2 mode check failed ')

    # Print after E2 mode assignment
    _LOG.debug("%s"%e2config)
