#!/usr/bin/env python
#
# Copyright (c) 2016, Juniper Networks, Inc.
# All rights reserved.
#
# Author (Abbas Sakarwala - abbas@juniper.net)
#
# This module has global MxRouter instantiation.
#

# Libraries/Modules
import os
import sys

sys.path.append(os.path.expanduser('../'))

from contrail_infra_client.provision_mxrouters import *

mx_router = MxRouter(' ')

