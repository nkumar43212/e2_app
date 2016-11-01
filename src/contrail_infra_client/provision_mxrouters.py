#File name:   provision_mxrouters.py
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

class MxRouter(object):

    def __init__(self, args_str):
        self._args = None
        if not args_str:
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
			    name])
        except NoIdError:
            pass
 
        if pr is None:
            bgp_router, pr = self.create_router(name, mgmt_ip, \
			    'Embe1mpls')
            pr.set_virtual_network(vn_obj)
            pr.set_physical_router_mx_type('contrail')
            self._vnc_lib.physical_router_update(pr)

    # end add_network_element

    def delete_network_element(self, name):
        print 'delete_network_element\n'

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
                    try:
                        fi_intf = self._vnc_lib.fabric_interface_read(fq_name=fi['to'])
                    except NoIdError:
                        continue
                    #pi_id = self._vnc_lib.physical_interface_delete(phy.get_fq_name())
                    #sometimes logical-interfaces are still hanging, so delete it
                    li_intf_list = fi_intf.get_logical_interfaces()
                    if li_intf_list is not None:
                        for li in li_intf_list:
                            li_id = self._vnc_lib.logical_interface_delete(li['to'])
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

        #get routing-protocols info
        rp = None
        try:
            rp = self._vnc_lib.routing_protocols_read(fq_name=[name])
        except NoIdError:
            pass

        #uuid = self._vnc_lib.get_default_routing_protocols_id()
        #self._vnc_lib.routing_protocols_delete(id=uuid)

        #delete 'physical-router' now.
        if pr is not None:
            self._vnc_lib.physical_router_delete(pr.get_fq_name())

        #delete routing-protocols now
        if rp is not None:
            self._vnc_lib.routing_protocols_delete(rp.get_fq_name())

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


    def add_network_physical_interfaces(self, name, phy_intf):
        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group,     \
			    name])
        except NoIdError:
            print 'phy-router lookup failed'
            return
 
        #physical-interface
        pi = None
        try:
            pi = self._vnc_lib.physical_interface_read(fq_name=[self._args.admin_tenant_group,  \
			    name, phy_intf])
        except NoIdError:
            pass

        if pi is None:
            pi = PhysicalInterface(phy_intf, parent_obj = pr)
            pi_id = self._vnc_lib.physical_interface_create(pi)
        else:
            print 'phy_intf lookup failed'
            return

        #update physical-router
        self._vnc_lib.physical_router_update(pr)

    # end add_network_physical_interfaces

    def delete_network_physical_interfaces(self, name, phy_intf):
        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    name])
        except NoIdError:
            print 'phy-router lookup failed'
            return

        #physical-interface lookup
        pi = None
        try:
            pi = self._vnc_lib.physical_interface_read(fq_name=[self._args.admin_tenant_group, \
			    name, phy_intf])
        except NoIdError:
            print 'phy-intf lookup failed'
            return

        #logical-interfaces
        li_intf_list = pi.get_logical_interfaces()
        if li_intf_list is not None:
            print 'logical interfaces exist, delete them first'
            return

        #physical-interface delete
        pi_id = self._vnc_lib.physical_interface_delete(pi.get_fq_name())
        self._vnc_lib.physical_router_update(pr)

    # end delete_network_physical_interfaces

    def add_network_logical_interfaces(self, name, phy_intf, logical_intf, vlan_tag,
                                       encap, family, ipaddress):

        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    name])
        except NoIdError:
            print 'phy-router lookup failed'
            return
 
        #physical-interface
        pi = None
        try:
            pi = self._vnc_lib.physical_interface_read(fq_name=[self._args.admin_tenant_group, \
			    name, phy_intf])
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
			    name, phy_intf, logical_intf])
        except NoIdError:
            pass
       
        if li is None:
            li = LogicalInterface(logical_intf, parent_obj = pi)
            if vlan_tag is not None:
                li.set_logical_interface_vlan_tag(int(vlan_tag))
            if family is not None:
                li.set_logical_interface_family(family)
            if ipaddress is not None:
                li.set_logical_interface_ipaddress(ipaddress)
            if encap is not None:
                li.set_logical_interface_encap_type(encap)
            li.set_virtual_machine_interface(vmi)
            li_id = self._vnc_lib.logical_interface_create(li)
            self._vnc_lib.physical_interface_update(pi)

        #update physical-router
        self._vnc_lib.physical_router_update(pr)

    # end add_network_logical_interfaces

    def add_network_logical_fi_interfaces(self, name, fabric_intf,
                                          logical_intf, vlan_tag, encap,
                                          family, ipaddress):

        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    name])
        except NoIdError:
	    print 'phy-router lookup failed'
            return

        #fabric-interface
        fi = None
        try:
            fi = self._vnc_lib.fabric_interface_read(fq_name=[self._args.admin_tenant_group, \
			    name, fabric_intf])
        except NoIdError:
	    print 'phy-intf lookup failed'
            return

        #logical-interface
        li = None
        try:
            li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			    name, fabric_intf, logical_intf])
        except NoIdError:
            pass

        if li is None:
            li = LogicalInterface(logical_intf, parent_obj = fi)
            if vlan_tag is not None:
                li.set_logical_interface_vlan_tag(int(vlan_tag))
            if family is not None:
                li.set_logical_interface_family(family)
            if ipaddress is not None:
                li.set_logical_interface_ipaddress(ipaddress)
            li_id = self._vnc_lib.logical_interface_create(li)
            self._vnc_lib.fabric_interface_update(fi)

        #update physical-router
        self._vnc_lib.physical_router_update(pr)

    # end add_network_logical_fi_interfaces

    def delete_network_logical_interfaces(self, name, phy_intf, logical_intf):
        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    name])
        except NoIdError:
            print 'phy-router lookup failed'
            return

        #physical-interface
        pi = None
        try:
            pi = self._vnc_lib.physical_interface_read(fq_name=[self._args.admin_tenant_group, \
			    name, phy_intf])
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
			    name, phy_intf, logical_intf])
        except NoIdError:
            print 'logical-intf lookup failed'
            return
       
        li.del_virtual_machine_interface(vmi)
        li_id = self._vnc_lib.logical_interface_delete(li.get_fq_name())

        #do we need to update any or else this is enough???
        pi_id = self._vnc_lib.physical_interface_update(pi)
        #update physical-router
        self._vnc_lib.physical_router_update(pr)

    # end delete_network_logical_interfaces

    def create_fabric_interface(self, name):
        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
                                                    name])
        except NoIdError:
            print 'phy-router lookup failed'
            return

        fi_intf_list = pr.get_fabric_interfaces()
        fi_index = 0
        if fi_intf_list is not None:
             fi_index = len(fi_intf_list)

        fi_intf = 'fi'
        fi_intf += str(fi_index)

        #fabric-interface
        fi = None
        try:
            fi = self._vnc_lib.fabric_interface_read(fq_name=[self._args.admin_tenant_group, \
                                                     name, fi_intf])
        except NoIdError:
            pass

        if fi is None:
            fi = FabricInterface(fi_intf, parent_obj = pr)
            pi_id = self._vnc_lib.fabric_interface_create(fi)

        self._vnc_lib.physical_router_update(pr)
        return fi_intf

    # end create_fabric_interface

    def delete_fabric_interface(self, name, fi_intf):
        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
                                                    name])
        except NoIdError:
            print 'phy-router lookup failed'
            return

        #delete the child interfaces as well.

        #fabric-interface
        fi = None
        try:
            fi = self._vnc_lib.fabric_interface_read(fq_name=[self._args.admin_tenant_group, \
			    name, fi_intf])
        except NoIdError:
	    print 'fi-intf lookup failed'
            return

        fi_id = self._vnc_lib.fabric_interface_delete(fi.get_fq_name())

        self._vnc_lib.physical_router_update(pr)

    # end delete_fabric_interface

    def add_child_interfaces_to_fabric(self, name, fi_intf, fab_phy_intfs):
        if not fab_phy_intfs:
            fab_phy_intfs = self._args.fab_phy_intfs

        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
                                                    name])
        except NoIdError:
            print 'phy-router lookup failed'
            return

        #fabric-interface
        fi = None
        try:
            fi = self._vnc_lib.fabric_interface_read(fq_name=[self._args.admin_tenant_group, \
                                                     name, fi_intf])
        except NoIdError:
            print 'fabric-intf lookup failed'
            return

        #child-interfaces to fabric-interface
        cfi = fi.fabric_child_interfaces

        if cfi:
            cfi = FabricInterfaceType('cfi', fab_phy_intfs)
        else:
            print 'child fabric-interfaces exist, adding more child to it'
            cfi = FabricInterfaceType('cfi', fab_phy_intfs)

        fi.set_fabric_child_interfaces(cfi)
        #physical-interface-type update
        if cfi is not None:
            cfi_list = cfi.get_fabric_physical_interface()
            for cfi_entry in cfi_list:
                pi = None
                try:
                    pi = self._vnc_lib.physical_interface_read(fq_name=[self._args.admin_tenant_group, \
			    name, cfi_entry])
                except NoIdError:
	            print 'phy-intf lookup failed'
                    continue;
                if pi:
                    phy_intf_type = PhysicalInterfaceType('gigether-options', fi_intf);
                    pi.set_physical_interface_type(phy_intf_type)
                    self._vnc_lib.physical_interface_update(pi)

        self._vnc_lib.fabric_interface_update(fi)

        # Do we need physical-router update???
        self._vnc_lib.physical_router_update(pr)

    # end add_child_interfaces_to_fabric

    def delete_child_interfaces_from_fabric(self, name, fi_intf, fab_phy_intfs):
        if not fab_phy_intfs:
            fab_phy_intfs = self._args.fab_phy_intfs

        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    name])
        except NoIdError:
            print 'phy-router lookup failed'
            return

        #fabric-interface
        fi = None
        try:
            fi = self._vnc_lib.fabric_interface_read(fq_name=[self._args.admin_tenant_group, \
			    name, fi_intf])
        except NoIdError:
            print 'fabric-intf lookup failed'
            return

        #child-interfaces to fabric-interface
        cfi = fi.get_fabric_child_interfaces()

        if cfi:
            print 'child fabric-interfaces exist for deletion'
            #cfi.delete_fabric_physical_interface(fab_phy_intfs[0])
            #cfi.delete_fabric_physical_interface(fab_phy_intfs[1])
        else:
            print 'no child fabric-interfaces exist, will delete none'
            return

        fi.set_fabric_child_interfaces([])
        self._vnc_lib.fabric_interface_update(fi)

        # Do we need physical-router update???
        self._vnc_lib.physical_router_update(pr)

    # end delete_child_interfaces_from_fabric

    def addService(self, access_name, access_rtr_id, access_intf, fi_intf, service_vlans, service_name, service_rtr_id):
        enable_service = False
        #physical-router
        mx_type = 'access'
        if mx_type is 'access':
            pr_access = None
            try:
                pr_access = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    access_name])
            except NoIdError:
	        print 'phy-router access lookup failed'
                return
            #physical-interface
            pi_access = None
            try:
                pi_access = self._vnc_lib.physical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        access_name, access_intf])
            except NoIdError:
	        print 'access_intf lookup on access failed'
                return
            if pr_access.physical_router_mx_type != 'access':
	        pr_access.set_physical_router_mx_type('access')
                self._vnc_lib.physical_router_update(pr_access)
                #physical-interface-type
                pi_access.set_physical_interface_encap_type('ethernet-ccc')
                self._vnc_lib.physical_interface_update(pi_access)
            #1. create logical-interface (access-port)
            access_li_ifl = access_intf + '.0'
            connect_vlan = None
            li_encap_type = None
            li_family = 'ccc'
            li_ipaddress = None
            #logical-interface
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        access_name, access_intf, access_li_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_interfaces(access_name, access_intf, \
			        access_li_ifl, connect_vlan, li_encap_type, li_family, li_ipaddress)
            #2. create logical-interface (fi)
            connect_vlan = None
            li_encap_type = None
            li_family = 'inet'
            li_ipaddress_base = '200.0.0.1/24'
            incr_val = int(filter(str.isdigit, fi_intf))
            incr_val += 200
            li_ipaddress_base = li_ipaddress_base.replace("200", str(incr_val))
            #li_ipaddress = '201.0.0.1/24'
            li_ipaddress = li_ipaddress_base;
            fi_li_ifl = fi_intf + '.0'
            #logical-interface
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        access_name, fi_intf, fi_li_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_fi_interfaces(access_name, fi_intf, \
			        fi_li_ifl, connect_vlan, li_encap_type, li_family, li_ipaddress)
            #3. create logical-interface (lo0)
            connect_vlan = None
            li_encap_type = None
            li_family = 'inet'
            lo0_intf = 'lo0'
            lo0_ifl = lo0_intf + '.0'
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        access_name, lo0_intf, lo0_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_interfaces(access_name, lo0_intf, \
			        lo0_ifl, connect_vlan, li_encap_type, li_family, access_rtr_id)
        #end of 'access'

        pr_service = None
        try:
            pr_service = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    service_name])
        except NoIdError:
	    print 'phy-router service lookup failed'
            return
 
        mx_type = 'service'
        access_intf = 'fi0'
        service_intf = 'ps0'
        if mx_type is 'service':
            #fabric-interface
            pi_service = None
            try:
                pi_service = self._vnc_lib.fabric_interface_read(fq_name=[self._args.admin_tenant_group, \
			        service_name, access_intf])
            except NoIdError:
	        print 'access_intf lookup on service failed'
                return
            if pr_service.physical_router_mx_type != 'service':
	        pr_service.set_physical_router_mx_type('service')
                self._vnc_lib.physical_router_update(pr_service)
            #1. create logical-interface (fi)
            access_li_ifl = access_intf + '.0'
            connect_vlan = None
            li_encap_type = None
            li_family = 'inet'
            li_ipaddress_base = '200.0.0.2/24'
            incr_val = int(filter(str.isdigit, fi_intf))
            incr_val += 200
            li_ipaddress_base = li_ipaddress_base.replace("200", str(incr_val))
            #li_ipaddress = '201.0.0.2/24'
            li_ipaddress = li_ipaddress_base;
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        service_name, access_intf, access_li_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_fi_interfaces(service_name, access_intf, \
			        access_li_ifl, connect_vlan, li_encap_type, li_family, li_ipaddress)
            #2. create logical-interface (ps)
            #physical-interface
            pi_svc = None
            try:
                pi_svc = self._vnc_lib.physical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        service_name, service_intf])
            except NoIdError:
                pass
            if pi_svc is None:
                pi_svc = PhysicalInterface(service_intf, parent_obj = pr_service)
                pi_id = self._vnc_lib.physical_interface_create(pi_svc)
                #update physical-router
                self._vnc_lib.physical_router_update(pr_service)
            connect_vlan = None
            li_encap_type = 'ethernet-ccc'
            li_family = None
            service_li_ifl = service_intf + '.0'
            li_ipaddress = None
            #logical-interface-1
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        service_name, service_intf, service_li_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_interfaces(service_name, service_intf, \
			                            service_li_ifl, connect_vlan, \
                                                    li_encap_type, li_family,  \
                                                    li_ipaddress)
            connect_vlan = 0
            incr = 0
            pi_svc_intf_count = len(pi_svc.get_logical_interfaces())
            enable_service = pi_svc_intf_count == 1
            pi_svc_intf_base = pi_svc_intf_count;
            pi_svc_intf_count += 109
            #walk thro's service vlan's and program 'ps' service ifls
            for connect_vlan in service_vlans:
                li_encap_type = None
                li_ipaddress_base = '110.0.0.1/24'
                incr_val = pi_svc_intf_count + incr
                li_ipaddress_base = li_ipaddress_base.replace("110", str(incr_val))
                li_ipaddress = li_ipaddress_base
                li_family = 'inet'
                service_li_ifl = service_intf + '.' + str(pi_svc_intf_base)
                li = None
                try:
                    li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			            service_name, service_intf, service_li_ifl])
                except NoIdError:
                    pass
       
                if li is None:
	            self.add_network_logical_interfaces(service_name, service_intf, \
			            service_li_ifl, connect_vlan, li_encap_type, li_family, li_ipaddress)
                incr +=1
                pi_svc_intf_base += incr
            #end of service-vlans

            #3. create logical-interface (lo0)
            connect_vlan = None
            li_encap_type = None
            li_family = 'inet'
            lo0_intf = 'lo0'
            lo0_ifl = lo0_intf + '.0'
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        service_name, lo0_intf, lo0_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_interfaces(service_name, lo0_intf, \
			        lo0_ifl, connect_vlan, li_encap_type, li_family, service_rtr_id)
        #end of 'service'
        #Add and activate the service now
        service_router_id = service_rtr_id.split('/', 1)
        access_router_id = access_rtr_id.split('/', 1)
        if enable_service:
            self.activateService(access_name, service_name, access_router_id[0], service_router_id[0])

    # end addServiceInternal

    def addServiceInternal(self, name, mx_type, access_intf, service_intf, service_vlans, lo0_ip):

        #physical-router
        pr = None
        try:
            pr = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    name])
        except NoIdError:
	    print 'phy-router lookup failed'
            return
 
        if mx_type is 'access':
            #physical-interface
            pi = None
            try:
                pi = self._vnc_lib.physical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        name, access_intf])
            except NoIdError:
	        print 'access_intf lookup on access failed'
                return
            if pr.physical_router_mx_type != 'access':
	        pr.set_physical_router_mx_type('access')
                self._vnc_lib.physical_router_update(pr)
            #physical-interface-type
            pi.set_physical_interface_encap_type('ethernet-ccc')
            self._vnc_lib.physical_interface_update(pi)
            #1. create logical-interface (access-port)
            access_li_ifl = access_intf + '.0'
            connect_vlan = None
            li_encap_type = None
            li_family = 'ccc'
            li_ipaddress = None
            #logical-interface
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        name, access_intf, access_li_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_interfaces(name, access_intf, \
			        access_li_ifl, connect_vlan, li_encap_type, li_family, li_ipaddress)
            #2. create logical-interface (fi)
            connect_vlan = None
            li_encap_type = None
            li_family = 'inet'
            li_ipaddress_base = '200.0.0.1/24'
            incr_val = int(filter(str.isdigit, access_intf))
            incr_val += 200
            li_ipaddress_base = li_ipaddress_base.replace("200", str(incr_val))
            #li_ipaddress = '201.0.0.1/24'
            li_ipaddress = li_ipaddress_base;
            service_li_ifl = service_intf + '.0'
            #logical-interface
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        name, service_intf, service_li_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_fi_interfaces(name, service_intf, \
			        service_li_ifl, connect_vlan, li_encap_type, li_family, li_ipaddress)
            #3. create logical-interface (lo0)
            connect_vlan = None
            li_encap_type = None
            li_family = 'inet'
            lo0_intf = 'lo0'
            lo0_ifl = lo0_intf + '.0'
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        name, lo0_intf, lo0_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_interfaces(name, lo0_intf, \
			        lo0_ifl, connect_vlan, li_encap_type, li_family, lo0_ip)

        if mx_type is 'service':
            #fabric-interface
            pi = None
            try:
                pi = self._vnc_lib.fabric_interface_read(fq_name=[self._args.admin_tenant_group, \
			        name, access_intf])
            except NoIdError:
	        print 'access_intf lookup on service failed'
                return
            if pr.physical_router_mx_type != 'service':
	        pr.set_physical_router_mx_type('service')
                self._vnc_lib.physical_router_update(pr)
            #1. create logical-interface (fi)
            access_li_ifl = access_intf + '.0'
            connect_vlan = None
            li_encap_type = None
            li_family = 'inet'
            li_ipaddress_base = '200.0.0.2/24'
            incr_val = int(filter(str.isdigit, name))
            incr_val += 200
            li_ipaddress_base = li_ipaddress_base.replace("200", str(incr_val))
            #li_ipaddress = '201.0.0.2/24'
            li_ipaddress = li_ipaddress_base;
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        name, access_intf, access_li_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_fi_interfaces(name, access_intf, \
			        access_li_ifl, connect_vlan, li_encap_type, li_family, li_ipaddress)
            #2. create logical-interface (ps)
            #physical-interface
            pi_svc = None
            try:
                pi_svc = self._vnc_lib.physical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        name, service_intf])
            except NoIdError:
                pass
            if pi_svc is None:
                pi_svc = PhysicalInterface(service_intf, parent_obj = pr)
                pi_id = self._vnc_lib.physical_interface_create(pi_svc)
                #update physical-router
                self._vnc_lib.physical_router_update(pr)
            connect_vlan = None
            li_encap_type = 'ethernet-ccc'
            li_family = None
            service_li_ifl = service_intf + '.0'
            li_ipaddress = None
            #logical-interface-1
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        name, service_intf, service_li_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_interfaces(name, service_intf, \
			                            service_li_ifl, connect_vlan, \
                                                    li_encap_type, li_family,  \
                                                    li_ipaddress)
            #logical-interface-2
            li_encap_type = None
            li_ipaddress = '110.0.0.1/24'
            li_family = 'inet'
            connect_vlan = '100'
            service_li_ifl = service_intf + '.1'
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        name, service_intf, service_li_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_interfaces(name, service_intf, \
			        service_li_ifl, connect_vlan, li_encap_type, li_family, li_ipaddress)
            #logical-interface-2
            li_ipaddress = '111.0.0.1/24'
            service_li_ifl = service_intf + '.2'
            connect_vlan = '101'
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        name, service_intf, service_li_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_interfaces(name, service_intf, \
			        service_li_ifl, connect_vlan, li_encap_type, li_family, li_ipaddress)
            #3. create logical-interface (lo0)
            connect_vlan = None
            li_encap_type = None
            li_family = 'inet'
            lo0_intf = 'lo0'
            lo0_ifl = lo0_intf + '.0'
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        name, lo0_intf, lo0_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_interfaces(name, lo0_intf, \
			        lo0_ifl, connect_vlan, li_encap_type, li_family, lo0_ip)

    # end addServiceInternal

    def activateService(self, access_name, service_name, access_rtr_id, service_rtr_id):

        #physical-router-access
        pr_access = None
        try:
            pr_access = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    access_name])
        except NoIdError:
	    print 'phy-router lookup failed'
            return

        #routing-protocols
        routing = None
        try:
            routing = self._vnc_lib.routing_protocols_read(fq_name=[access_name])
        except NoIdError:
	    print 'routing-protocols doesnt exist- create one'
            pass
	if not routing:
	    routing = RoutingProtocols(name=access_name)

            #physical-interface, fabric-interface list
            phy_intf_list, fi_intf_list = self.get_pi_fi_list(pr_access)
            if phy_intf_list is None or fi_intf_list is None:
	        print 'no interfaces to enable'
                return
            #ldp
	    ldp_params = LdpProtocolParams(phy_intf_list)
            routing.set_routing_protocol_ldp(ldp_params)
            #ospf
            ospf_params = OspfProtocolParams()
            ospf_params.area = '0.0.0.0'
            ospf_params.interface_name = phy_intf_list
            routing.set_routing_protocol_ospf(ospf_params)
            #mpls
            mpls_params = MplsProtocolParams(fi_intf_list)
            routing.set_routing_protocol_mpls(mpls_params)
            #l2-ckt
            l2ckt_params = L2cktProtocolParams()
            l2ckt_params.virtual_ckt_id = 1
            l2ckt_params.identifier = service_rtr_id
            l2ckt_params.interface_name = 'ge-0/0/0.0'
            routing.set_routing_protocol_l2ckt(l2ckt_params)
            self._vnc_lib.routing_protocols_create(routing)
            #pr_access.set_routing_protocols(routing)

        pr_access.set_routing_protocols(routing)
        pr_id = self._vnc_lib.physical_router_update(pr_access)


        #physical-router-service
        pr_service = None
        try:
            pr_service = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    service_name])
        except NoIdError:
	    print 'phy-router lookup failed'
            return

        #routing-protocols
        routing = None
        try:
            routing = self._vnc_lib.routing_protocols_read(fq_name=[service_name])
        except NoIdError:
	    print 'routing-protocols doesnt exist- create one'
            pass
	if not routing:
	    routing = RoutingProtocols(name=service_name)

            #physical-interface, fabric-interface list
            phy_intf_list, fi_intf_list = self.get_pi_fi_list(pr_service)
            if phy_intf_list is None or fi_intf_list is None:
	        print 'no interfaces to enable'
                return
            #ldp
	    ldp_params = LdpProtocolParams(phy_intf_list)
            routing.set_routing_protocol_ldp(ldp_params)
            #ospf
            ospf_params = OspfProtocolParams()
            ospf_params.area = '0.0.0.0'
            ospf_params.interface_name = phy_intf_list
            routing.set_routing_protocol_ospf(ospf_params)
            #mpls
            mpls_params = MplsProtocolParams(fi_intf_list)
            routing.set_routing_protocol_mpls(mpls_params)
            #l2-ckt
            l2ckt_params = L2cktProtocolParams()
            l2ckt_params.virtual_ckt_id = 1
            l2ckt_params.identifier = access_rtr_id
            l2ckt_params.interface_name = 'ps0.0'
            routing.set_routing_protocol_l2ckt(l2ckt_params)
            self._vnc_lib.routing_protocols_create(routing)
            #pr_service.set_routing_protocols(routing)

        pr_service.set_routing_protocols(routing)
        pr_id = self._vnc_lib.physical_router_update(pr_service)

    # end activateService

    def moveService(self, access_name, access_rtr_id, access_intf, fi_intf, service_vlans, service_name, service_rtr_id):

        #physical-router
        pr_access = None
        try:
            pr_access = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    access_name])
        except NoIdError:
	    print 'phy-router access lookup failed'
            return
 
        mx_type = 'access'
        if mx_type is 'access':
            #physical-interface
            pi_access = None
            try:
                pi_access = self._vnc_lib.physical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        access_name, access_intf])
            except NoIdError:
	        print 'access_intf lookup on access failed'
                return
            if pr_access.physical_router_mx_type != 'access':
	        pr_access.set_physical_router_mx_type('access')
                self._vnc_lib.physical_router_update(pr_access)
                #physical-interface-type
                pi_access.set_physical_interface_encap_type('ethernet-ccc')
                self._vnc_lib.physical_interface_update(pi_access)
            #2. create logical-interface (fi)
            connect_vlan = None
            li_encap_type = None
            li_family = 'inet'
            li_ipaddress_base = '200.0.0.1/24'
            incr_val = int(filter(str.isdigit, fi_intf))
            incr_val += 200
            li_ipaddress_base = li_ipaddress_base.replace("200", str(incr_val))
            #li_ipaddress = '201.0.0.1/24'
            li_ipaddress = li_ipaddress_base;
            fi_li_ifl = fi_intf + '.0'
            #logical-interface
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        access_name, fi_intf, fi_li_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_fi_interfaces(access_name, fi_intf, \
			        fi_li_ifl, connect_vlan, li_encap_type, li_family, li_ipaddress)
        #end of 'access'

        pr_service = None
        try:
            pr_service = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    service_name])
        except NoIdError:
	    print 'phy-router service lookup failed'
            return
 
        mx_type = 'service'
        #service should always have one 'fi' and one 'ps(for now)'
        access_intf = 'fi0'
        service_intf = 'ps0'
        if mx_type is 'service':
            #fabric-interface
            pi_service = None
            try:
                pi_service = self._vnc_lib.fabric_interface_read(fq_name=[self._args.admin_tenant_group, \
			        service_name, access_intf])
            except NoIdError:
	        print 'access_intf lookup on service failed'
                return
            if pr_service.physical_router_mx_type != 'service':
	        pr_service.set_physical_router_mx_type('service')
                self._vnc_lib.physical_router_update(pr_service)
            #1. create logical-interface (fi)
            access_li_ifl = access_intf + '.0'
            connect_vlan = None
            li_encap_type = None
            li_family = 'inet'
            li_ipaddress_base = '200.0.0.2/24'
            incr_val = int(filter(str.isdigit, fi_intf))
            incr_val += 200
            li_ipaddress_base = li_ipaddress_base.replace("200", str(incr_val))
            #li_ipaddress = '201.0.0.2/24'
            li_ipaddress = li_ipaddress_base;
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        service_name, access_intf, access_li_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_fi_interfaces(service_name, access_intf, \
			        access_li_ifl, connect_vlan, li_encap_type, li_family, li_ipaddress)
            #2. create logical-interface (ps)
            #physical-interface
            pi_svc = None
            try:
                pi_svc = self._vnc_lib.physical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        service_name, service_intf])
            except NoIdError:
                pass
            if pi_svc is None:
                pi_svc = PhysicalInterface(service_intf, parent_obj = pr_service)
                pi_id = self._vnc_lib.physical_interface_create(pi_svc)
                #update physical-router
                self._vnc_lib.physical_router_update(pr_service)
            self._vnc_lib.physical_router_update(pr_service)
            connect_vlan = None
            li_encap_type = 'ethernet-ccc'
            li_family = None
            service_li_ifl = service_intf + '.0'
            li_ipaddress = None
            #logical-interface-1
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        service_name, service_intf, service_li_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_interfaces(service_name, service_intf, \
			                            service_li_ifl, connect_vlan, \
                                                    li_encap_type, li_family,  \
                                                    li_ipaddress)
            connect_vlan = 0
            incr = 0
            pi_svc_intf_count = len(pi_svc.get_logical_interfaces())
            pi_svc_intf_base = pi_svc_intf_count;
            pi_svc_intf_count += 109
            #walk thro's service vlan's and program 'ps' service ifls
            for connect_vlan in service_vlans:
                li_encap_type = None
                li_ipaddress_base = '110.0.0.1/24'
                incr_val = pi_svc_intf_count + incr
                li_ipaddress_base = li_ipaddress_base.replace("110", str(incr_val))
                li_ipaddress = li_ipaddress_base
                li_family = 'inet'
                service_li_ifl = service_intf + '.' + str(pi_svc_intf_base)
                li = None
                try:
                    li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			            service_name, service_intf, service_li_ifl])
                except NoIdError:
                    pass
       
                if li is None:
	            self.add_network_logical_interfaces(service_name, service_intf, \
			            service_li_ifl, connect_vlan, li_encap_type, li_family, li_ipaddress)
                incr +=1
                pi_svc_intf_base += incr
            #end of service-vlans

            #3. create logical-interface (lo0)
            connect_vlan = None
            li_encap_type = None
            li_family = 'inet'
            lo0_intf = 'lo0'
            lo0_ifl = lo0_intf + '.0'
            li = None
            try:
                li = self._vnc_lib.logical_interface_read(fq_name=[self._args.admin_tenant_group, \
			        service_name, lo0_intf, lo0_ifl])
            except NoIdError:
                pass
       
            if li is None:
	        self.add_network_logical_interfaces(service_name, lo0_intf, \
			        lo0_ifl, connect_vlan, li_encap_type, li_family, service_rtr_id)
        #end of 'service'
        #Move the service now
        service_router_id = service_rtr_id.split('/', 1)
        access_router_id = access_rtr_id.split('/', 1)
        self.moveServiceInternal(access_name, service_name, access_router_id[0], service_router_id[0])

    # end moveService

    def moveServiceInternal(self, access_name, svc_name, access_rtr_id, service_rtr_id):

        #physical-router-access
        pr_access = None
        try:
            pr_access = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    access_name])
        except NoIdError:
	    print 'phy-router lookup failed'
            return

        #routing-protocols
        routing = None
        try:
            routing = self._vnc_lib.routing_protocols_read(fq_name=[access_name])
        except NoIdError:
	    print 'access- routing-protocols lookup failed'
            return

        #physical-interface, fabric-interface list
        phy_intf_list, fi_intf_list = self.get_pi_fi_list(pr_access)
        if phy_intf_list is None or fi_intf_list is None:
	    print 'no interfaces to enable'
            return

        #ldp
	ldp_params = LdpProtocolParams(phy_intf_list)
        routing.set_routing_protocol_ldp(ldp_params)
        #ospf
        ospf_params = OspfProtocolParams()
        ospf_params.area = '0.0.0.0'
        ospf_params.interface_name = phy_intf_list
        routing.set_routing_protocol_ospf(ospf_params)
        #mpls
        mpls_params = MplsProtocolParams(fi_intf_list)
        routing.set_routing_protocol_mpls(mpls_params)
        #l2-ckt
        l2ckt_params = L2cktProtocolParams()
        l2ckt_params.virtual_ckt_id = 1
        l2ckt_params.identifier = service_rtr_id
        l2ckt_params.interface_name = 'ge-0/0/0.0'
        routing.set_routing_protocol_l2ckt(l2ckt_params)
        self._vnc_lib.routing_protocols_update(routing)

        pr_id = self._vnc_lib.physical_router_update(pr_access)

        #physical-router-service
        pr_service = None
        try:
            pr_service = self._vnc_lib.physical_router_read(fq_name=[self._args.admin_tenant_group, \
			    svc_name])
        except NoIdError:
	    print 'phy-router lookup failed'
            return

        #routing-protocols
        routing = None
        try:
            routing = self._vnc_lib.routing_protocols_read(fq_name=[svc_name])
        except NoIdError:
	    print 'routing-protocols doesnt exist- create one'
            pass
	if not routing:
	    routing = RoutingProtocols(name=svc_name)

            #physical-interface, fabric-interface list
            phy_intf_list, fi_intf_list = self.get_pi_fi_list(pr_service)
            if phy_intf_list is None or fi_intf_list is None:
	        print 'no interfaces to enable'
                return
            #ldp
	    ldp_params = LdpProtocolParams(phy_intf_list)
            routing.set_routing_protocol_ldp(ldp_params)
            #ospf
            ospf_params = OspfProtocolParams()
            ospf_params.area = '0.0.0.0'
            ospf_params.interface_name = phy_intf_list
            routing.set_routing_protocol_ospf(ospf_params)
            #mpls
            mpls_params = MplsProtocolParams(fi_intf_list)
            routing.set_routing_protocol_mpls(mpls_params)
            #l2-ckt
            l2ckt_params = L2cktProtocolParams()
            l2ckt_params.virtual_ckt_id = 1
            l2ckt_params.identifier = access_rtr_id
            l2ckt_params.interface_name = 'ps0.0'
            routing.set_routing_protocol_l2ckt(l2ckt_params)
            self._vnc_lib.routing_protocols_create(routing)
            pr_service.set_routing_protocols(routing)

        pr_id = self._vnc_lib.physical_router_update(pr_service)
 
    # end moveServiceInternal

    def deleteService(self, access_name, acces_rtr_id, access_intf, fi_intf, service_vlans, service_name, service_rtr_id):
        print "deleteService called"

    # end deleteService

    def get_pi_fi_list(self, pr):
        #physical-interface
        phy_intf_list = pr.get_physical_interfaces()
        pi_list = [];
        fi_list = [];
        pi_fi_name = None
        if phy_intf_list is not None:
	    for phy in phy_intf_list:
                try:
                    pi = self._vnc_lib.physical_interface_read(fq_name=phy['to'])
                except NoIdError:
                    continue
                if pi.name.startswith("lo0"):
                    pi_fi_name = str(pi.name) + ".0"
                    pi_list.append(pi_fi_name)
        #fabric-interface
        fi_intf_list = pr.get_fabric_interfaces()
        if fi_intf_list is not None:
	    for fi in fi_intf_list:
                try:
                    fi_intf = self._vnc_lib.fabric_interface_read(fq_name=fi['to'])
                except NoIdError:
                    continue
                if fi_intf.name.startswith("fi"):
                    pi_fi_name = str(fi_intf.name) + ".0"
                    pi_list.append(pi_fi_name)
                    fi_list.append(pi_fi_name)
        return pi_list, fi_list

    # end get_pi_fi_list

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
            'fi_index': 1,
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

    #mx_router.add_network_element('vmxAccess', '169.254.0.11')
    #mx_router.add_network_element('vmxService01', '169.254.0.20')
    #mx_router.add_network_element('vmxService02', '169.254.0.27')

    #mx_router.delete_network_element('vmxAccess')
    #mx_router.delete_network_element('vmxService01')
    #mx_router.delete_network_element('vmxService02')


    #mx_router.add_network_physical_interfaces('vmxAccess', 'ge-0/0/0')
    #mx_router.add_network_physical_interfaces('vmxAccess', 'ge-0/0/1')
    #mx_router.add_network_physical_interfaces('vmxAccess', 'ge-0/0/2')
    #mx_router.add_network_physical_interfaces('vmxAccess', 'lo0')

    #mx_router.add_network_physical_interfaces('vmxService01', 'ge-0/0/0')
    #mx_router.add_network_physical_interfaces('vmxService01', 'ge-0/0/1')
    #mx_router.add_network_physical_interfaces('vmxService01', 'lo0')

    #mx_router.add_network_physical_interfaces('vmxService02', 'ge-0/0/0')
    #mx_router.add_network_physical_interfaces('vmxService02', 'ge-0/0/1')
    #mx_router.add_network_physical_interfaces('vmxService02', 'lo0')

    #fi = mx_router.create_fabric_interface('vmxAccess')
    #fab_phy_intfs0 = ['ge-0/0/1']
    #mx_router.add_child_interfaces_to_fabric('vmxAccess', fi, fab_phy_intfs0)

    #fi = mx_router.create_fabric_interface('vmxAccess')
    #fab_phy_intfs0 = ['ge-0/0/2']
    #mx_router.add_child_interfaces_to_fabric('vmxAccess', fi, fab_phy_intfs0)

    #fi = mx_router.create_fabric_interface('vmxService01')
    #fab_phy_intfs0 = ['ge-0/0/0']
    #mx_router.add_child_interfaces_to_fabric('vmxService01', fi, fab_phy_intfs0)

    #fi = mx_router.create_fabric_interface('vmxService02')
    #fab_phy_intfs0 = ['ge-0/0/0']
    #mx_router.add_child_interfaces_to_fabric('vmxService02', fi, fab_phy_intfs0)

    #service_vlans = []
    #access = mx_router.addServiceInternal('vmxAccess', 'access', 'ge-0/0/0', 'fi0', service_vlans, '1.1.1.1/32')

    #service_vlans = []
    #service_vlans = ['100','101']
    #service1 = mx_router.addService('vmxAccess', '1.1.1.1/32', 'ge-0/0/0', 'fi0', 
                                    #service_vlans, 'vmxService01', '2.2.2.2/32')

    #service_vlans = ['103']
    #service1 = mx_router.addService('vmxAccess', '1.1.1.1/32', 'ge-0/0/0', 'fi0', 
                                    #service_vlans, 'vmxService01', '2.2.2.2/32')
    #service_vlans = ['150', '151']
    #service1 = mx_router.addService('vmxAccess', '1.1.1.1/32', 'ge-0/0/0', 'fi1', 
    #                                service_vlans, 'vmxService01', '3.3.3.3/32')
    #service_vlans = ['100','101']
    #service1 = mx_router.addServiceInternal('vmxService01', 'service', 'fi0', 'ps0', service_vlans, '2.2.2.2/32')

    #mx_router.activateService('vmxAccess', 'vmxService01', '1.1.1.1', '2.2.2.2')

    #service_vlans = ['100','101']
    #service2 = mx_router.addServiceInternal('vmxService02', 'service', 'fi0', 'ps0', service_vlans, '3.3.3.3/32')

    #service_vlans = ['100','101', '103']
    #service1 = mx_router.moveService('vmxAccess', '1.1.1.1/32', 'ge-0/0/0', 'fi1', 
    #                                 service_vlans, 'vmxService02', '3.3.3.3/32')
    #service_vlans = "all"
    #service1 = mx_router.deleteService('vmxAccess', '1.1.1.1/32', 'fi0', 
                                    #service_vlans, 'vmxService01', '2.2.2.2/32')
    #mx_router.moveServiceInternal('vmxAccess', 'vmxService01', '1.1.1.1', '2.2.2.2')
    #mx_router.moveServiceInternal('vmxAccess', 'vmxService02', '1.1.1.1', '3.3.3.3')

# end main

if __name__ == "__main__":
    main()

