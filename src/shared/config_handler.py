#!/usr/bin/env python
#
# Copyright (c) 2016, Juniper Networks, Inc.
# All rights reserved.
#
# Author (Abbas Sakarwala - abbas@juniper.net)
#
# This module is config handler class for Elastic Edge Application
# to handle loading and saving of configuration files.
#

# Libraries/Modules
import os
import sys
import argparse
import ConfigParser
import traceback
from config import E2Config
from constants import E2Constants as e2consts

class E2ConfigHandler:
    """
    E2ConfigHandler class to
    1. Load configuration
    2. Override configuration from e2_config.ini file
    """

    # track the visited files
    files_visited = set()

    def __init__(self):
        self.e2_cfg = E2Config()

    def mode_check(self, mode):
        if mode not in e2consts.MODE:
            raise argparse.ArgumentTypeError(
                "E2 mode can only be one of the following:\n" +
                "\t" + e2consts.MODE_ADJ_API + "\n" +
                "\t" + e2consts.MODE_ADJ_DISCOVER + "\n")
        return mode

    def config_file_check(self, file):
        """
        Function to check if the user supplied configuration file exists or not
        """
        if not os.path.exists(file):
            raise argparse.ArgumentTypeError(
                "Config file does not exist.")
        return file

    def config_handle(self, cfg_file):
        """
        Parse E2 configuration file.
        """
        config = ConfigParser.ConfigParser()
        config.read(cfg_file)
        E2ConfigHandler.files_visited.add(cfg_file)

        try:
            # print "Before read\n-----------\n" + str(self.e2_cfg)

            # Read arguments from configuration file
            # Read mode, host, http_port
            SECTION = "E2_APPLICATION"
            if config.has_section(SECTION):
                if config.has_option(SECTION, "mode"):
                    self.e2_cfg.mode = config.get(SECTION, "mode")
                if config.has_option(SECTION, "host"):
                    self.e2_cfg.host = config.get(SECTION, "host")
                if config.has_option(SECTION, "http_port"):
                    self.e2_cfg.http_port = config.getint(SECTION, "http_port")

            # Read na_ctrl config
            SECTION = "LOGGING"
            if config.has_section(SECTION):
                if config.has_option(SECTION, "path"):
                    self.e2_cfg.log_file_path = config.get(SECTION, "path")
                if config.has_option(SECTION, "file"):
                    self.e2_cfg.log_file_name = config.get(SECTION, "file")
                if config.has_option(SECTION, "level"):
                    self.e2_cfg.log_level = config.get(SECTION, "level")

            # print "After read\n-----------\n" + str(self.e2_cfg)

        except ConfigParser.NoOptionError as e:
            return (False, "error: {0}".format(e.message))

        except ValueError as e:
            return (False, "error: {0}".format(e.message))

        # TODO: This exception is not being caught?
        except ConfigParser.ParsingError:
            return (False, "Config file has parsing errors")

        return (True, "Config ok")

    def version_str_get(self):
        """
        A routine to build NA version string
        """
        str = ": %s\n" % self.e2_cfg.version
        str += "Copyright (c) 2016, Juniper Networks, Inc.\n"
        str += "All rights reserved."
        return str

    def options_handle(self):
        """
        Handle NA command line options
        """
        # Parse command line arguments
        parser = argparse.ArgumentParser(prog='Elastic Edge Application')
        group = parser.add_mutually_exclusive_group()

        try:
            parser.add_argument("action",
                                choices=['start', 'stop', 'restart', 'status'],
                                help="Action to perform: start|stop|restart|status")
            parser.add_argument("-c", "--config_file",
                                metavar="config file",
                                action="store",
                                dest="config_file",
                                help="E2 configuration file",
                                type=self.config_file_check)
            parser.add_argument('-v', '--version',
                                action='version',
                                version='%(prog)s' + self.version_str_get())
            args = parser.parse_args()

            # Parse service action
            self.e2_cfg.action = args.action

            # Save config file
            if (args.config_file is None) :
                sys.exit("Config file must be specified for E2")

            # Parse config file
            err, err_msg = self.config_handle(args.config_file)
            if False == err:
                sys.exit("Config file validation failed " + err_msg)

            # Parse stop and status actions
            if args.action == 'stop' or args.action == 'status':
                return

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_tb(exc_tb)
            sys.exit("Configuration parse failed.")

# Main function
if __name__ == "__main__":
    # Create E2ConfigHandler object to parse config file and input arguments
    config_handler = E2ConfigHandler()
    config_handler.options_handle()
