import cvp
from cvplibrary import Form
from cvplibrary import CVPGlobalVariables, GlobalVariableNames
from jinja2 import Template
import re

# Login to CVP API
username = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_USERNAME)
password = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_PASSWORD)
server = cvp.Cvp("localhost")
server.authenticate(username, password)

# Retrieve Form Data
vlan = Form.getFieldById("vlan").getValue()
name = Form.getFieldById("name").getValue()
tenant = Form.getFieldById("tenant").getValue()
gateway = Form.getFieldById("gateway").getValue()
mask = Form.getFieldById("mask").getValue()

# Pull in relavent Jinja2 Tempaltes via CVP API
# Templates are stored as normal static configlets
try:
  vlan_template_configlet = server.cvpService.getConfigletByName("L3LS-v Vlan Template")
  vlan_template = Template(vlan_template_configlet["config"])
except cvp.cvpServices.CvpError as e:
  if str(e).startswith("132801"):
    print "L3LS-v Vlan Template configlet does not exist.  Exiting..."

# Render Vlan Template for Config Application
# Create dictionary based on Field inputs for feeding purposes
if gateway != None:
  vlan_info = {
    "vlan_id" : vlan,
    "vlan_name" : name,
    "tenant_id" : tenant,
    "gateway" : gateway,
    "mask" : mask
  }
else:
  vlan_info = {
    "vlan_id" : vlan,
    "vlan_name" : name
  }
vlan_config = vlan_template.render(vlan_info=vlan_info)

# Retrieve Existing Tenant Config from configlet named "L3LS-v Tenant Vlans"
try:
  tenant_vlan_configlet = server.cvpService.getConfigletByName("L3LS-v Tenant Vlans")
  old_config = tenant_vlan_configlet["config"]
  # Add new vlan config to existing configlet
  new_vlan_config = old_config + vlan_config
  # Generate configlet class object
  final_vlan_configlet = cvp.Configlet("L3LS-v Tenant Vlans", new_vlan_config)
  # Update configlet and return task IDs
  tasks = server.updateConfiglet(final_vlan_configlet, waitForTaskIds=True)
  print "L3LS-v Tenant Vlans Configlet updated. The following task IDs have been created. Execute them to push changes.\n"
  for task in tasks:
    print task
# If no Vlan config exists, create new configlet and apply to container named "L3LS-v Leaves"
except cvp.cvpServices.CvpError as e:
  if str(e).startswith("132801"):
    print "L3LS-v Tenant Vlans configlet does not exist. Creating...\n"
    base_vlan_configlet = cvp.Configlet("L3LS-v Tenant Vlans", vlan_config)
    server.addConfiglet(base_vlan_configlet)
    # Apply Configlet to Leafs Container
    print "\nApplying new configlet to L3LS-v Leaves Container...\n"
    base_vlan_configlet = [base_vlan_configlet]
    container_class = server.getContainer("L3LS-v Leaves")
    tasks = server.mapConfigletToContainer(container_class, base_vlan_configlet)
    print "\nConfiglet applied. The following task IDs have been created. Execute them to push changes.\n"
    for task in tasks:
      print "Task \"" + task + "\""
print ""