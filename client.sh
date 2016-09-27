#!/bin/bash

host_ip=$1
host_port=$2

# Default
if [ -z $host_ip ] ; then
    host_ip="localhost"
fi

if [ -z $host_port ] ; then
    host_port=10001
fi

# Util
pause () {
   read -p "$*"
}

echo "Host IP = $host_ip"
echo "Host Port = $host_port"
pause 'Press [Enter] key to continue or [Ctrl+C] to exit ...'
echo ''

# Create access node
curl --verbose -X POST -H "Content-Type: application/json" -H "Cache-Control: no-cache" -d '{ "name":"vmxAccess", "mgmt_ip": "169.254.0.22", "role": "access" }' "http://${host_ip}:${host_port}/network-elements"
echo; echo

# Create service node
curl --verbose -X POST -H "Content-Type: application/json" -H "Cache-Control: no-cache" -d '{ "name":"vmxService", "mgmt_ip": "169.254.0.20", "role": "service" }' "http://${host_ip}:${host_port}/network-elements"
echo; echo

# Create conn-link
curl --verbose -X POST -H "Content-Type: application/json" -H "Cache-Control: no-cache" -d '{ "name":"conn-one", "left_node": "vmxAccess", "left_links": ["ge-0/0/1", "ge-0/0/2"], "right_node": "vmxService", "right_links": ["ge-1/0/1", "ge-2/0/2"], "fabric": null }' "http://${host_ip}:${host_port}/conn-links"
echo; echo

# Get all nodes
curl --verbose -X GET -H "Content-Type: application/json" -H "Cache-Control: no-cache" "http://${host_ip}:${host_port}/network-elements"
echo; echo

# Get all conn-links
curl -verbose -X GET -H "Content-Type: application/json" -H "Cache-Control: no-cache" "http://${host_ip}:${host_port}/conn-links"
echo; echo

# Remove conn-link
curl --verbose -X DELETE -H "Content-Type: application/json" -H "Cache-Control: no-cache" "http://${host_ip}:${host_port}/conn-links/conn-one"
echo; echo

# Remove access-node
curl --verbose -X DELETE -H "Content-Type: application/json" -H "Cache-Control: no-cache" "http://${host_ip}:${host_port}/network-elements/vmxAccess"
echo; echo

# Remove service-node
curl --verbose -X DELETE -H "Content-Type: application/json" -H "Cache-Control: no-cache" "http://${host_ip}:${host_port}/network-elements/vmxService"
echo; echo

