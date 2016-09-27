# e2_app
Elastic Edge Application

# To start the E2 application:
* python e2_app.py -c ../config/e2_config.ini start
  === or ===
* python2.7 e2_app.py -c ../config/e2_config.ini start

Note: Currently "start/stop" actions are not implement. **TBD for future**.
      However, E2 app webservice will start listening at the port defined 
      in e2_config.ini

# Src code layout:
* 1. src/webservice --- REST API implementation
* 2. src/contrail_infra_client --- Client APIs into the contrail infra
* 3. src/infra --- commonly used one time basic infra code
* 4. src/shared --- specific to E2 for now

# Client curl commands to add/delete Network Element and ConnLink:
* Sample example: ./client.sh <<<host_ip>>> <<<host_port>>>
  if host_ip and host_port is not provided, default = localhost, 10001

