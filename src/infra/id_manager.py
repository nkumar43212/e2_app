#!/usr/bin/env python
#
# Copyright (c) 2016, Juniper Networks, Inc.
# All rights reserved.
#
# Author (Abbas Sakarwala - abbas@juniper.net)
#
# This module is a simple unique id allocator class
#

# Libraries/Modules
class IdManagerException(Exception): pass

class IdManager(object):
    def __init__(self, n):
        if isinstance(n, int):
            self.max = n
            self.ids = set(range(1, n + 1))
        elif isinstance(n, list) or isinstance(n, set):
            self.max = len(n)
            self.ids = set(n)
        else:
            self.max = 0
            self.ids = set()
        self.orig_ids = self.ids.copy()

    def get_id(self):
        try:
            return self.ids.pop()
        except KeyError:
            raise IdManagerException("no available ids")

    def free_id(self, n):
        if n not in self.orig_ids:
            raise IdManagerException("cannot free id %d not in original set" % (n))
        self.ids.add(n) # no-op if n already there, do we care?

# Main function
if __name__ == "__main__":
    for i in range(0, 3):
        if i == 0:
            # Create a id manager - with n as int
            print "IdManager as int:"
            id_manager = IdManager(254)
        elif i == 1:
            # Create a id manager - with n as list
            print "IdManager as list:"
            id_manager = IdManager([51, 61, 71, 81, 91, 81, 71])
        else:
            # Create a id manager - with n as set
            print "IdManager as set:"
            id_manager = IdManager({51, 61, 71, 81, 91})
        id1 = id_manager.get_id()
        print "get", id1
        id2 = id_manager.get_id()
        print "get", id2
        # Special handling for int
        if i == 0:
            for x in range(0, 100):
                tmp_id = id_manager.get_id()
                print "get", tmp_id
        id_manager.free_id(id1)
        print "free", id1
        print id_manager.ids
        # print id_manager.orig_ids
        idm = id_manager.get_id()
        print "get", idm
        print id_manager.ids
        # print id_manager.orig_ids
        print ""
