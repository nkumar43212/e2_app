#File name:   provision_simple_interfaces.py
#!/usr/bin/python
#
# Copyright (c) 2016-17 Juniper Networks, Inc. All rights reserved.
#
#python provision_mxrouters.py


import argparse
import ConfigParser

import json
import copy
from netaddr import IPNetwork

from vnc_api.vnc_api import *


def get_ip(ip_w_pfx):
    return str(IPNetwork(ip_w_pfx).ip)
# end get_ip

class NetworkElement(object):

    def __init__(self, name, mgmt_ip):
        self._name    = name
        self._mgmt_ip = mgmt_ip
      

class MxRouter(object):

    def __init__(self, args_str):
        self._args = None
	self.mxrouters = {}
	self.mxrouters_id = {}
        if args_str == None:
            args_str = ' '.join(sys.argv[1:])
        self._parse_args(args_str)

        self._vnc_lib = VncApi(self._args.admin_user,
                               self._args.admin_password,
                               self._args.admin_tenant_name,
                               self._args.api_server_ip,
                               self._args.api_server_port, '/')

    # end __init__
    def __iter__(self):
        return iter(self._args._mxrouters)
    # end __iter__

    def _get_ip_fabric_ri_obj(self):
        # TODO pick fqname hardcode from common
        rt_inst_obj = self._vnc_lib.routing_instance_read(
            fq_name=['default-domain', 'default-project',
                     'ip-fabric', '__default__'])

        return rt_inst_obj
    # end _get_ip_fabric_ri_obj

    def create_router(self, name, mgmt_ip, password):
        bgp_router = BgpRouter(name, parent_obj=self._get_ip_fabric_ri_obj())
        params = BgpRouterParams()
        params.address = mgmt_ip
        params.address_families = AddressFamilies(['route-target', 'inet-vpn', 'e-vpn',
                                             'inet6-vpn'])
        params.autonomous_system = 64512
        params.vendor = 'mx'
        params.identifier = mgmt_ip
        bgp_router.set_bgp_router_parameters(params)
        self._vnc_lib.bgp_router_create(bgp_router)

        pr = PhysicalRouter(name)
        pr.physical_router_management_ip = mgmt_ip
        pr.physical_router_vendor_name = 'juniper'
        pr.physical_router_product_name = 'mx'
        pr.physical_router_vnc_managed = True
        uc = UserCredentials('root', password)
        pr.set_physical_router_user_credentials(uc)
        pr.set_bgp_router(bgp_router)
        pr_id = self._vnc_lib.physical_router_create(pr)
        return bgp_router, pr
    # end create_router

    def add_network_element(self, name, mgmt_ip):
	network_element = self.mxrouters.get(name)
        if not network_element:
            network_element = NetworkElement(name, mgmt_ip)
            self.mxrouters_id[id(network_element)] = network_element
            self.mxrouters[name] = network_element
        #ipam
        ipam_obj = None
        ipam_name = 'ipam1'
        ipam_name += name
        try:
            ipam_obj = self._vnc_lib.network_ipam_read(fq_name=[self._args.admin_tenant_name, \
			    self._args.admin_tenant_project, ipam_name])
        except NoIdError:
            pass
        if ipam_obj is None:
            ipam_obj = NetworkIpam(ipam_name)
            self._vnc_lib.network_ipam_create(ipam_obj)

        #virtual-network
        vn_obj = None
        vn_name = 'vn1'
        vn_name += name
        try:
            vn_obj = self._vnc_lib.virtual_network_read(fq_name=[self._args.admin_tenant_name, \
			    self._args.admin_tenant_project, vn_name])
        except NoIdError:
            pass
 
        if vn_obj is None: 
            vn_obj = VirtualNetwork(vn_name)

            vn_obj.add_network_ipam(ipam_obj, VnSubnetsType([IpamSubnetType(SubnetType("10.0.0.0", \
						    24))]))
            vn1_uuid = self._vnc_lib.virtual_network_create(vn_obj)

        vni_obj_properties = vn_obj.get_virtual_network_properties() or VirtualNetworkType()
        #set the virtual-network to be 'mx' type.
        vni_obj_properties.set_forwarding_mode('mx')
        vn_obj.set_virtual_network_properties(vni_obj_properties)
        self._vnc_lib.virtual_network_update(vn_obj)

        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    network_element._name])
        except NoIdError:
            pass
 
        if pr is None:
            bgp_router, pr = self.create_router(network_element._name, network_element._mgmt_ip, \
			    'Embe1mpls')
            pr.set_virtual_network(vn_obj)
            self._vnc_lib.physical_router_update(pr)

    # end add_network_element

    def delete_network_element(self, name):
        print 'delete_network_element\n'
        network_element = self.mxrouters.get(name)

        if network_element:
            print network_element._name
            print network_element._mgmt_ip
            del self.mxrouters_id[id(network_element)]
            del self.mxrouters[network_element._name]

        #import pdb; pdb.set_trace()
        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, name])
        except NoIdError:
            pass
        if pr is not None:
            #logical-interfaces
            li_intf_list = pr.get_logical_interfaces()
            if li_intf_list is not None:
                for li in li_intf_list:
                    li_id = self._vnc_lib.logical_interface_delete(li['to'])
            #physical-interface
            phy_intf_list = pr.get_physical_interfaces()
            if phy_intf_list is not None:
                for phy in phy_intf_list:
                    try:
                        pi = self._vnc_lib.physical_interface_read(fq_name=phy['to'])
                    except NoIdError:
                        continue
                    #pi_id = self._vnc_lib.physical_interface_delete(phy.get_fq_name())
                    #sometimes logical-interfaces are still hanging, so delete it
                    li_intf_list = pi.get_logical_interfaces()
                    if li_intf_list is not None:
                        for li in li_intf_list:
                            li_id = self._vnc_lib.logical_interface_delete(li['to'])
                    pi_id = self._vnc_lib.physical_interface_delete(phy['to'])
            #fabric-interfaces
            fi_intf_list = pr.get_fabric_interfaces()
            if fi_intf_list is not None:
                for fi in fi_intf_list:
                    fi_id = self._vnc_lib.fabric_interface_delete(fi['to'])

        #virtual-machine-interface
        vmi = None
        vmi_name = 'vmi1'
        #vmi_name = 'vn1'
        vmi_name += name
        try:
            vmi = self._vnc_lib.virtual_machine_interface_read(fq_name=[self._args.admin_tenant_name, \
			    self._args.admin_tenant_project, vmi_name])
        except NoIdError:
            pass
        if vmi is not None:
            self._vnc_lib.virtual_machine_interface_delete(vmi.get_fq_name())

        #delete 'physical-router' now.
        if pr is not None:
            self._vnc_lib.physical_router_delete(pr.get_fq_name())

        #bgp-router
        br = None
        try:
            br = self._vnc_lib.bgp_router_read(fq_name=[self._args.admin_tenant_name, \
			    self._args.admin_tenant_project, u'ip-fabric', u'__default__', name])
        except NoIdError:
            pass
 
        if br is not None:
            self._vnc_lib.bgp_router_delete(br.get_fq_name())

        #virtual-network
        vn_obj = None
        vn_name = 'vn1'
        vn_name += name
        try:
            vn_obj = self._vnc_lib.virtual_network_read(fq_name=[self._args.admin_tenant_name, \
			    self._args.admin_tenant_project, vn_name])
        except NoIdError:
            pass
 
        if vn_obj is not None: 
            vn1_uuid = self._vnc_lib.virtual_network_delete(vn_obj.get_fq_name())

        #ipam
        ipam_obj = None
        ipam_name = 'ipam1'
        ipam_name += name
        try:
            ipam_obj = self._vnc_lib.network_ipam_read(fq_name=[self._args.admin_tenant_name, \
			    self._args.admin_tenant_project, ipam_name])
        except NoIdError:
            pass
        if ipam_obj is not None:
            self._vnc_lib.network_ipam_delete(ipam_obj.get_fq_name())

	return 0
    # end delete_network_element

    def get_network_element(self, name):
        network_element = self.mxrouters.get(name)

        return network_element

    def show_all_network_elements(self):
        for name in list(self.mxrouters):
            network_element = self.get_network_element(name)
            #print "router:%s, ip %d" %s (network_element._name, network_element._mgmt_ip)
            print network_element._name
            print network_element._mgmt_ip
            print "----------"

    def add_network_physical_interfaces(self, name, mgmt_ip, phy_intf):
	network_element = self.mxrouters.get(name)
        if not network_element:
            network_element = NetworkElement(name, mgmt_ip)
            self.mxrouters_id[id(network_element)] = network_element
            self.mxrouters[name] = network_element

        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    network_element._name])
        except NoIdError:
	    print 'phy-router lookup failed'
            return
 
        #physical-interface
        pi = None
        try:
            pi = self._vnc_lib.physical_interface_read(fq_name=[self._args.admin_tenant_group, \
			    network_element._name, phy_intf])
        except NoIdError:
            pass

        if pi is None:
            pi = PhysicalInterface(phy_intf, parent_obj = pr)
            pi_id = self._vnc_lib.physical_interface_create(pi)
        else:
            print 'phy_intf already exists'
            return

        #update physical-router
        self._vnc_lib.physical_router_update(pr)

    # end add_network_physical_interfaces

    def del_network_physical_interfaces(self, name, mgmt_ip, phy_intf):
	network_element = self.mxrouters.get(name)
        if not network_element:
            network_element = NetworkElement(name, mgmt_ip)
            self.mxrouters_id[id(network_element)] = network_element
            self.mxrouters[name] = network_element

        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    network_element._name])
        except NoIdError:
	    print 'phy-router lookup failed'
            return

        #physical-interface lookup
        pi = None
        try:
            pi = self._vnc_lib.physical_interface_read(fq_name=[self._args.admin_tenant_group, \
			    network_element._name, phy_intf])
        except NoIdError:
	    print 'phy-intf lookup failed'
            return

        #logical-interfaces
        li_intf_list = pi.get_logical_interfaces()
        if li_intf_list is not None:
            print 'logical interfaces exist, delete them first'
            return;

        #physical-interface delete
        pi_id = self._vnc_lib.physical_interface_delete(pi.get_fq_name())
        self._vnc_lib.physical_router_update(pr)

    # end del_network_physical_interfaces

    def add_network_logical_interfaces(self, name, mgmt_ip, phy_intf, logical_intf, vlan_tag):
	network_element = self.mxrouters.get(name)
        if not network_element:
            network_element = NetworkElement(name, mgmt_ip)
            self.mxrouters_id[id(network_element)] = network_element
            self.mxrouters[name] = network_element

        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    network_element._name])
        except NoIdError:
	    print 'phy-router lookup failed'
            return
 
        #physical-interface
        pi = None
        try:
            pi = self._vnc_lib.physical_interface_read(fq_name=[self._args.admin_tenant_group, \
			    network_element._name, phy_intf])
        except NoIdError:
	    print 'phy-intf lookup failed'
            return

        #virtual-network
        vn_obj = None
        vn_name = 'vn1'
        vn_name += name
        try:
            vn_obj = self._vnc_lib.virtual_network_read(fq_name=[self._args.admin_tenant_name, \
			    self._args.admin_tenant_project, vn_name])
        except NoIdError:
            pass
 
        if vn_obj is None:
            vn_obj = VirtualNetwork(vn_name)

            vn_obj.add_network_ipam(ipam_obj, VnSubnetsType([IpamSubnetType(SubnetType("10.0.0.0", \
						    24))]))
            vn1_uuid = self._vnc_lib.virtual_network_create(vn_obj)
            vni_obj_properties = vn_obj.get_virtual_network_properties() or VirtualNetworkType()
            #set the virtual-network to be 'mx' type.
            vni_obj_properties.set_forwarding_mode('mx')
            vn_obj.set_virtual_network_properties(vni_obj_properties)
            self._vnc_lib.virtual_network_update(vn_obj)

        #virtual-machine-interface
        vmi_name = 'vmi1'
        vmi_name += name
        vmi = None
        try:
            vmi = self._vnc_lib.virtual_machine_interface_read(fq_name=[self._args.admin_tenant_name, \
			    self._args.admin_tenant_project, vmi_name])
        except NoIdError:
            pass

        if vmi is None:
            vmi = VirtualMachineInterface(fq_name=[self._args.admin_tenant_name, \
                            self._args.admin_tenant_project, vmi_name] , parent_type='project')
            vmi.set_virtual_network(vn_obj)
            vmi.device_owner = 'physicalrouter'
            self._vnc_lib.virtual_machine_interface_create(vmi)

        #logical-interface
        li = None
        try:
            li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			    network_element._name, phy_intf, logical_intf])
        except NoIdError:
            pass
       
        if li is None:
            li = LogicalInterface(logical_intf, parent_obj = pi)
            li.set_logical_interface_vlan_tag(int(vlan_tag))
            li.set_virtual_machine_interface(vmi)
            li_id = self._vnc_lib.logical_interface_create(li)

        #update physical-router
        self._vnc_lib.physical_router_update(pr)

    # end add_network_logical_interfaces

    def del_network_logical_interfaces(self, name, mgmt_ip, phy_intf, logical_intf):
	network_element = self.mxrouters.get(name)
        if not network_element:
            network_element = NetworkElement(name, mgmt_ip)
            self.mxrouters_id[id(network_element)] = network_element
            self.mxrouters[name] = network_element

        #physical-interface
        pi = None
        try:
            pi = self._vnc_lib.physical_interface_read(fq_name=[self._args.admin_tenant_group, \
			    network_element._name, phy_intf])
        except NoIdError:
	    print 'phy-intf lookup failed'
            return

        #virtual-machine-interface
        vmi_name = 'vmi1'
        vmi_name += name
        vmi = None
        try:
            vmi = self._vnc_lib.virtual_machine_interface_read(fq_name=[self._args.admin_tenant_name, \
			    self._args.admin_tenant_project, vmi_name])
        except NoIdError:
	    print 'vmi-intf lookup failed'
            return

        #logical-interface
        li = None
        try:
            li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			    network_element._name, phy_intf, logical_intf])
        except NoIdError:
	    print 'logical-intf lookup failed'
            return
       
        li.del_virtual_machine_interface(vmi)
        li_id = self._vnc_lib.logical_interface_delete(li.get_fq_name())

        #do we need to update any or else this is enough???
        pi_id = self._vnc_lib.physical_interface_update(pi)

    # end del_network_logical_interfaces

    def create_fabric_interface(self, name, mgmt_ip):
        network_element = self.mxrouters.get(name)
        if not network_element:
            network_element = NetworkElement(name, mgmt_ip)
            self.mxrouters_id[id(network_element)] = network_element
            self.mxrouters[name] = network_element

        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
                                                    network_element._name])
        except NoIdError:
            print 'phy-router lookup failed'
            return

        fi_intf = 'fi'
        fi_intf += str(self._args.fi_index)
        self._args.fi_index += 1

        #fabric-interface
        fi = None
        try:
            fi = self._vnc_lib.fabric_interface_read(fq_name=[self._args.admin_tenant_group, \
                                                     network_element._name, fi_intf])
        except NoIdError:
            pass

        if fi is None:
            fi = FabricInterface(fi_intf, parent_obj = pr)
            pi_id = self._vnc_lib.fabric_interface_create(fi)

        self._vnc_lib.physical_router_update(pr)
        return fi_intf

    # end create_fabric_interface

    def delete_fabric_interface(self, name, mgmt_ip, fi_intf):
        network_element = self.mxrouters.get(name)
        if not network_element:
            network_element = NetworkElement(name, mgmt_ip)
            self.mxrouters_id[id(network_element)] = network_element
            self.mxrouters[name] = network_element

        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
                                                    network_element._name])
        except NoIdError:
            print 'phy-router lookup failed'
            return

        #delete the child interfaces as well.

        #fabric-interface
        fi = None
        try:
            fi = self._vnc_lib.fabric_interface_read(fq_name=[self._args.admin_tenant_group, \
                                                     network_element._name, fi_intf])
        except NoIdError:
            print 'fi-intf lookup failed'
            return

        fi_id = self._vnc_lib.fabric_interface_delete(fi.get_fq_name())

        self._vnc_lib.physical_router_update(pr)

    # end delete_fabric_interface

    def add_child_intefaces_to_fabric(self, name, mgmt_ip, fi_intf, fab_phy_intfs):
        network_element = self.mxrouters.get(name)
        if not network_element:
            network_element = NetworkElement(name, mgmt_ip)
            self.mxrouters_id[id(network_element)] = network_element
            self.mxrouters[name] = network_element

        if not fab_phy_intfs:
            fab_phy_intfs = self._args.fab_phy_intfs

        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
                                                    network_element._name])
        except NoIdError:
            print 'phy-router lookup failed'
            return

        #fabric-interface
        fi = None
        try:
            fi = self._vnc_lib.fabric_interface_read(fq_name=[self._args.admin_tenant_group, \
			    network_element._name, fi_intf])
        except NoIdError:
	    print 'fabric-intf lookup failed'
            return

        #child-interfaces to fabric-interface
        cfi = fi.fabric_child_interfaces

        if cfi:
            cfi = FabricInterfaceType('cfi', fab_phy_intfs)
        else:
            print 'child fabric-interfaces exist'
            cfi = FabricInterfaceType('cfi', fab_phy_intfs)

        fi.set_fabric_child_interfaces(cfi)
        self._vnc_lib.fabric_interface_update(fi)

        # Do we need physical-router update???
        self._vnc_lib.physical_router_update(pr)

    # end add_child_inteface_to_fabric

    def del_child_intefaces_from_fabric(self, name, mgmt_ip, fi_intf, fab_phy_intfs):
        network_element = self.mxrouters.get(name)
        if not network_element:
            network_element = NetworkElement(name, mgmt_ip)
            self.mxrouters_id[id(network_element)] = network_element
            self.mxrouters[name] = network_element

        if not fab_phy_intfs:
            fab_phy_intfs = self._args.fab_phy_intfs

        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
                                                    network_element._name])
        except NoIdError:
            print 'phy-router lookup failed'
            return

        #fabric-interface
        fi = None
        try:
            fi = self._vnc_lib.fabric_interface_read(fq_name=[self._args.admin_tenant_group, \
                                                     network_element._name, fi_intf])
        except NoIdError:
            print 'fabric-intf lookup failed'
            return

        #child-interfaces to fabric-interface
        cfi = fi.get_fabric_child_interfaces()

        if cfi:
            print 'child fabric-interfaces exist'
            #cfi.delete_fabric_physical_interface(fab_phy_intfs[0])
            #cfi.delete_fabric_physical_interface(fab_phy_intfs[1])
        else:
            print 'no child fabric-interfaces exist'
            return

        #import pdb; pdb.set_trace()
        fi.set_fabric_child_interfaces([])
        self._vnc_lib.fabric_interface_update(fi)

        # Do we need physical-router update???
        self._vnc_lib.physical_router_update(pr)

    # end del_child_intefaces_from_fabric

    def addService(self, name, mgmt_ip, service_vlan):
        network_element = self.mxrouters.get(name)
        if not network_element:
            network_element = NetworkElement(name, mgmt_ip)
            self.mxrouters_id[id(network_element)] = network_element
            self.mxrouters[name] = network_element

        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
                                                    network_element._name])
        except NoIdError:
            print 'phy-router lookup failed'
            return

    # end addService

    def removeService(self, name, mgmt_ip, service_vlan):
        network_element_svc = self.mxrouters.get(name)

        if not network_element_svc:
            print 'ne svc not present'
            return

        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
                                                    network_element_svc._name])
        except NoIdError:
            print 'phy-router lookup failed'
            return

    # end removeService

    def moveService(self, access_name, from_svc_name, to_svc_name):
        network_element_access = self.mxrouters.get(access_name)
        network_element_from_svc = self.mxrouters.get(from_svc_name)
        network_element_to_svc = self.mxrouters.get(to_svc_name)

        if not network_element_access:
            print 'ne access not present'
            return

        if not network_element_from_svc:
            print 'ne from_svc not present'
            return

        if not network_element_to_svc:
            print 'ne to_svc not present'
            return

        #physical-router
        pr_access = None
        try:
            pr_access = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
                                                           network_element_access._name])
        except NoIdError:
            print 'phy-router lookup failed'
            return
        #physical-router
        pr_from_svc = None
        try:
            pr_from_svc = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
                                                             network_element_access._name])
        except NoIdError:
            print 'phy-router lookup failed'
            return
        #physical-router
        pr_to_svc = None
        try:
            pr_to_svc = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
                                                           network_element_access._name])
        except NoIdError:
            print 'phy-router lookup failed'
            return

    # end moveService

    def _parse_args(self, args_str):
        '''
        Eg. python provision_physical_router.py 
                                   --api_server_ip 127.0.0.1
                                   --api_server_port 8082
        '''

        # Source any specified config/ini file
        # Turn off help, so we print all options in response to -h
        conf_parser = argparse.ArgumentParser(add_help=False)

        conf_parser.add_argument("-c", "--conf_file",
                                 help="Specify config file", metavar="FILE")
        args, remaining_argv = conf_parser.parse_known_args(args_str.split())

        defaults = {
            #'public_vn_name': 'default-domain:'
            #'default-project:default-virtual-network',
            'api_server_ip': '127.0.0.1',
            'api_server_port': '8082',
        }
        ksopts = {
            'admin_user': 'admin',
            'admin_password': 'secret123',
            'admin_tenant_name': 'default-domain',
        }
        default_misc = {
            'admin_tenant_group': 'default-global-system-config',
            'admin_tenant_project': 'default-project',
            'router_password': 'Embe1mpls',
        }

        default_intf = {
            'physical_intfs': ['ge-0/0/0', 'ge-0/0/1'],
            'logical_intfs': ['ge-0/0/0.0', 'ge-0/0/1.0'],
            'vlan_tag': '100',
        }

        default_fi = {
            'fi_index': 0,
            'fabric_intf': 'fi0',
            'fab_phy_intfs': ['ge-0/0/0', 'ge-0/0/1'],
        }
        if args.conf_file:
            config = ConfigParser.SafeConfigParser()
            config.read([args.conf_file])
            defaults.update(dict(config.items("DEFAULTS")))
            default_misc.update(dict(config.items("DEFAULTS")))
            default_intf.update(dict(config.items("DEFAULTS")))
            default_fi.update(dict(config.items("DEFAULTS")))
            if 'KEYSTONE' in config.sections():
                ksopts.update(dict(config.items("KEYSTONE")))

        # Override with CLI options
        # Don't surpress add_help here so it will handle -h
        parser = argparse.ArgumentParser(
            # Inherit options from config_parser
            parents=[conf_parser],
            # print script description with -h/--help
            description=__doc__,
            # Don't mess with format of description
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )
        defaults.update(ksopts)
        defaults.update(default_misc)
        defaults.update(default_intf)
        defaults.update(default_fi)
        parser.set_defaults(**defaults)

        parser.add_argument(
            "--api_server_ip", help="IP address of api server", required=False)
        parser.add_argument("--api_server_port", help="Port of api server", required=False)
        parser.add_argument(
            "--admin_user", help="Name of keystone admin user", required=False)
        parser.add_argument(
            "--admin_password", help="Password of keystone admin user", required=False)
        parser.add_argument(
            "--admin_tenant_name", help="Tenamt name for keystone admin user", required=False)

        parser.add_argument(
            "--op", help="operation (add_basic, delete_basic, fip_test)", required=False)

        parser.add_argument(
            "--public_vrf_test", help="operation (False, True)", required=False)
        parser.add_argument(
            "--mxrouter", help="MX gateway ", required=False)

        self._args = parser.parse_args(remaining_argv)

    # end _parse_args

# end class MxRouter


def main(args_str=None):
    mx_router = MxRouter(None)
    import pdb; pdb.set_trace()
    #mx_router.add_network_element('vmxAccess', '169.254.0.11')
    #mx_router.delete_network_element('vmxAccess')
    ##mx_router.add_network_element('vmxService01', '169.254.0.20')
    ##mx_router.add_network_element('vmxService02', '169.254.0.27')

    print "--- show all elements---"
    #mx_router.show_all_network_elements()

#    #import pdb; pdb.set_trace()
#    print "--- deleting  vmxService01 ---"
#    mx_router.delete_network_element('vmxService01')
#    print "--- showing remaining elements---"
#    mx_router.show_all_network_elements()
#    print "--- deleting  vmx4 ---"
#    mx_router.delete_network_element('vmx4')
#    print "--- showing remaining elements---"
#    mx_router.show_all_network_elements()
#    print "--- deleting  vmx4 ---"
#    mx_router.delete_network_element('vmx5')
#    print "--- showing remaining elements---"
#    print "--- deleting  vmxService ---"
#    mx_router.delete_network_element('vmxService')
#    print "--- showing remaining elements---"
    mx_router.add_network_physical_interfaces('vmxAccess', '192.254.0.11', 'ge-0/0/0')
    mx_router.add_network_physical_interfaces('vmxAccess', '192.254.0.11', 'ge-0/0/1')
    ##mx_router.add_network_physical_interfaces('vmxService01', '192.254.0.20', 'ge-0/0/1')
    ##mx_router.add_network_physical_interfaces('vmxService02', '192.254.0.27', 'ge-0/0/1')
    #import pdb; pdb.set_trace()
    mx_router.add_network_logical_interfaces('vmxAccess', '192.254.0.11', 'ge-0/0/0', 'ge-0/0/0.0', '101')
    ##mx_router.add_network_logical_interfaces('vmxService01', '192.254.0.20', 'ge-0/0/1', 'ge-0/0/1.0', '102')
    #mx_router.del_network_logical_interfaces('vmxService01', '192.254.0.20', 'ge-0/0/1', 'ge-0/0/1.0')
    #mx_router.del_network_logical_interfaces('vmxService01', '192.254.0.20', 'ge-0/0/0', 'ge-0/0/0.1')
    #mx_router.del_network_logical_interfaces('vmxAccess', '192.254.0.20', 'ge-0/0/0', 'ge-0/0/0.0')
    #mx_router.del_network_physical_interfaces('vmxAccess', '192.254.0.20', 'ge-0/0/0')
    fi = mx_router.create_fabric_interface('vmxAccess', '192.254.0.11')
    fab_phy_intfs0 = ['ge-0/0/1']
    mx_router.add_child_intefaces_to_fabric('vmxAccess', '192.254.0.11', fi, fab_phy_intfs0)
    fi = mx_router.create_fabric_interface('vmxAccess', '192.254.0.11')
    fab_phy_intfs0 = ['ge-0/0/2']
    mx_router.add_child_intefaces_to_fabric('vmxAccess', '192.254.0.11', fi, fab_phy_intfs0)
    ##self._args.fi_index = 0
    ##fi = mx_router.create_fabric_interface('vmxService01', '192.254.0.20')
    ##fab_phy_intfs1 = ['ge-0/0/0']
    ##mx_router.add_child_intefaces_to_fabric('vmxService01', '192.254.0.20', fi, fab_phy_intfs1)
    ##self._args.fi_index = 0
    ##fi = mx_router.create_fabric_interface('vmxService02', '192.254.0.27')
    ##fab_phy_intfs1 = ['ge-0/0/0']
    ##mx_router.add_child_intefaces_to_fabric('vmxService02', '192.254.0.27', fi, fab_phy_intfs1)
    #fab_phy_intfs = []
    #mx_router.del_child_intefaces_from_fabric('vmxService01', '192.254.0.20', 'fi0', fab_phy_intfs)
#    print "--- showing remaining fabric elements---"
#    mx_router.show_all_fabric_elements()
    ##mx_router.del_child_intefaces_from_fabric('vmxService01', '192.254.0.20', 'fi0', fab_phy_intfs0)
    ##mx_router.delete_fabric_interface('vmxService01', '192.254.0.20', 'fi0')
    ##mx_router.del_child_intefaces_from_fabric('vmxService01', '192.254.0.20', 'fi1', fab_phy_intfs1)
    ##mx_router.delete_fabric_interface('vmxService01', '192.254.0.20', 'fi1')
    #mx_router.delete_network_element('vmx0')
    #mx_router.delete_network_element('vmxService01')
    #import pdb; pdb.set_trace()
    #mx_router.delete_network_element('vmxAccess')
    #mx_router.delete_network_element('vmx01')
    ##mx_router.addService('vmxService01', '192.254.0.20', '101')
    ##mx_router.addService('vmxService01', '192.254.0.20', '102')
    ##mx_router.addService('vmxService02', '192.254.0.27', '101')
    ##mx_router.addService('vmxService02', '192.254.0.27', '102')
    ##mx_router.activateService('vmxAccess', 'vmxService01')
    ##mx_router.moveService('vmxAccess', 'vmxService01', 'vmxService02')

# end main

if __name__ == "__main__":
    main()

