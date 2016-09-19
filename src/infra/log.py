#!/usr/bin/env python
#
# Copyright (c) 2016, Juniper Networks, Inc.
# All rights reserved.
#
# Author (Abbas Sakarwala - abbas@juniper.net)
#
# This module defines the NA logging functions
#
# The way this is supposed to be used is this - There will be one root
# logger defined per process. The logging handler will be defined at
# the root logger. The module-specific loggers will not define
# handlers, they can, however, define their own logging level. The
# limitation of this model is that module-specific loggers cannot have
# their own log format or handlers
# 
# This module needs to be used in a way that all the RootLoggers and
# it's module loggers are logging to a different file. Therefore the
# users need to ensure that there are different log files per
# process. If two processes use the same log file the log file output
# can get jumbled in places.
#

import sys
import logging
import logging.handlers
import threading
import time

# Mapping of 
str_py_lvl = {
    "criticial": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
    "all": logging.NOTSET
}

# Define the NA default log format
FILE_FMT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
SYSLOG_FMT = '%(name)s - %(levelname)s - %(message)s'


# RootLogger - This is only created at the top of a process
class RootLogger(object):
    def __init__(self, name, level, fname=None, max_size=0, max_backups=0):
        self.fname = fname
        self.max_size = max_size
        self.max_backups = max_backups
        self.root_name = name
        self.logger = logging.getLogger(name)

        self.logger.setLevel(self.get_level(level))
        if fname is None:
            # TODO --- check this address on mac and linux
            # Check for supported platforms
            if sys.platform.startswith('linux'):
                handler = logging.handlers.SysLogHandler(address='/dev/log')
            elif sys.platform.startswith('darwin'):
                handler = logging.handlers.SysLogHandler(address='/var/run/syslog')
            else:
                raise Exception("Platform %s not supported." % sys.platform)
            formatter = logging.Formatter(SYSLOG_FMT)
        else:
            handler = logging.handlers.RotatingFileHandler(
                fname, maxBytes=max_size, backupCount=max_backups)
            formatter = logging.Formatter(FILE_FMT)

        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

    def __getattr__(self, attrname):
        return getattr(self.logger, attrname)

    def get_level(self, level):
        try:
            py_level = str_py_lvl[level.lower()]
        except KeyError:
            _LOG.error("Bad level given %s", str(level))
            py_level = None
        return py_level

    def set_handler(self, fname, max_size=0, max_backups=0, format=FILE_FMT):
        handler = logging.handlers.RotatingFileHandler(
            fname, maxBytes=max_size, backupCount=max_backups)
        root_logger = logging.getLogger(self.root_name)
        formatter = logging.Formatter(format)
        handler.setFormatter(formatter)
        # Remove existing handler.
        root_logger.handlers = []
        root_logger.addHandler(handler)

    def set_level(self, level):
        py_level = self.get_level(level)
        if py_level is not None:
            root_logger = logging.getLogger(self.root_name)
            root_logger.setLevel(self.get_level(level))


# Module logger - is created by every module for logging from that
# module
class Logger(object):
    def __init__(self, root_name, module, level="info"):
        self.root_name = root_name
        self.my_name = root_name + "." + module
        self.logger = logging.getLogger(self.my_name)
        self.set_level(level)

    def __getattr__(self, attrname):
        return getattr(self.logger, attrname)

    # Routine to enable module logger to change the handler
    def set_handler(self, fname, max_size=0, max_backups=0, format=FILE_FMT):
        handler = logging.handlers.RotatingFileHandler(
            fname, maxBytes=max_size, backupCount=max_backups)
        # Change the handler in the root logger so that all module
        # loggers are affectted too.
        root_logger = logging.getLogger(self.root_name)
        # Reset the formatter in case the previous handler was syslog
        formatter = logging.Formatter(format)
        handler.setFormatter(formatter)
        # Remove existing handler.
        root_logger.handlers = []

        root_logger.addHandler(handler)

    # Get the logging level set for this module
    def get_level(self, level):
        try:
            py_level = str_py_lvl[level.lower()]
        except KeyError:
            _LOG.error("Bad level given %s", str(level))
            py_level = None
        return py_level

    # Set the logging level for this module logger
    def set_level(self, level):
        py_level = self.get_level(level)
        if py_level is not None:
            logger = logging.getLogger(self.my_name)
            logger.setLevel(self.get_level(level))


# Self test
if __name__ == "__main__":
    def test_func(root_name):
        ML3 = Logger(root_name, __name__)
        ML3.set_handler(root_name + ".log", 100000, 2, "")
        ML3.debug("Module 3 logger created")
        for i in range(9):
            # Some of these messages will get logged to syslog and
            # some to the handler set in the ML3.set_handler call
            # below
            if i % 2:
                ML3.debug("Module 3 test_func i=%d", i)
            else:
                # Only this values will go in file as info is default level
                ML3.info("Module 3 test_func i=%d", i)
            time.sleep(1)


    # Create a root logger for this process
    RL = RootLogger("RL", "debug")
    # Log s message to the root logger. This message should go to the
    # syslog
    RL.debug("Created the root logger")

    # Create a thread and log from the thread.
    thread = threading.Thread(target=test_func, args=("M3",))
    thread.start()
    time.sleep(5)

    # Create module logger
    ML1 = Logger("RL", "M1")
    # Log to this module logger. This should go to the syslog.
    ML1.debug("Module 1 logger created")

    # Create another module logger
    ML2 = Logger("RL", "M2")
    # Log to this module logger. This should go to the syslog.
    ML2.debug("Module 2 logger created")

    # Now change the handler for all the loggers to a file. Now all of
    # the messages below and some of the messages from the thread will
    # get logger to the file
    ML2.set_handler("M2.log", 100000, 2)
    for i in range(10):
        # Root logger too will log to the file even though the logger
        # was changed in the module logger.
        RL.debug("Logging to root logger with a file handle (iter=%d)" % i)
        # ML1 module logger too will log to the file even though the
        # logger was changed in the module logger.
        ML1.debug("Logging to module 1 with a file handle (iter=%d)" % i)
        # ML2 module logger will log to the file as the logger was
        # changed in this module's logger.
        ML2.debug("Logging to module 2 with a file handle (iter=%d)" % i)

    thread.join()
