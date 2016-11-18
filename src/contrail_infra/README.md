# contrail infrastructure
This module contains the following

* 1. schema --- Contains E2 schema
* 2. device-manager --- Contains changes that translates E2 config to NETCONF

Note: The schema has to be copied to build directory and compiled to generate
      the REST API's.
      The device-manager files are either copied to the target location or 
      else built to form a contrail package. Copying files to target 
      location requires start/stop of contrail-device-manager.
