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
    self.max = n
    self.ids = set(range(1, n + 1))

  def get_id(self):
    try:
      return self.ids.pop()
    except KeyError:
      raise IdManagerException("no available ids")

  def free_id(self, n):
    if n > self.max:
      raise IdManagerException("id %d out of range (max %d)" % (n, self.max))

    self.ids.add(n) # no-op if n already there, do we care?

# Main function
if __name__ == "__main__":
    # Create a id manager
    id_manager = IdManager(254)
    id1 = id_manager.get_id()
    print id1
    id2 = id_manager.get_id()
    print id2
    for x in range(0, 100):
        tmp_id = id_manager.get_id()
        print tmp_id
    id_manager.free_id(id1)
    print id_manager.ids
    idm = id_manager.get_id()
    print idm
    print id_manager.ids
