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
tenant_id = Form.getFieldById("tenant_id").getValue()
fw_vlan_id = Form.getFieldById("fw_vlan_id").getValue()
fw_gateway = Form.getFieldById("fw_gateway").getValue()

# Pull in relavent Jinja2 Tempaltes via CVP API
# Templates are stored as normal static configlets
try:
  tenant_template_configlet = server.cvpService.getConfigletByName("L3LS-v Tenant Template")
  tenant_template = Template(tenant_template_configlet["config"])
except cvp.cvpServices.CvpError as e:
  if str(e).startswith("132801"):
    print "L3LS-v Tenant Template configlet does not exist.  Exiting..."
try:
  fw_template_configlet = server.cvpService.getConfigletByName("L3LS-v FW Template")
  fw_template = Template(fw_template_configlet["config"])
except cvp.cvpServices.CvpError as e:
  if str(e).startswith("132801"):
    print "L3LS-v FW Template configlet does not exist.  Exiting..."

# Parse out various IPs from Gateway
ip_list = fw_gateway.split(".")
fw_prefix = str(ip_list[0]) + "." + str(ip_list[1]) + "." + str(ip_list[2])
gateway_ip = ip_list[3]
switch_ip = ip_list[3]
fw_ip = str(int(ip_list[3]) + 3)
border_leaves = ["L3LS-V-LEAF-1A", "L3LS-V-LEAF-1B"]
border_config = {}

# Render Tenant Template for Config Application
# Create dictionary based on Field Inputs for feeding purposes
tenant_info = {
  "tenant_id" : tenant_id,
  "fw_vlan_id" : fw_vlan_id,
  "gateway_ip" : gateway_ip,
  "fw_prefix" : fw_prefix,
  "fw_ip" : fw_ip,
  "switch_ip" : switch_ip
}
tenant_config = tenant_template.render(tenant_info=tenant_info)
for leaf in border_leaves:
  switch_ip = str(int(switch_ip) + 1)
  tenant_info.update(switch_ip = switch_ip)
  fw_config = fw_template.render(tenant_info=tenant_info)
  border_config.update( { leaf : fw_config } )

# First apply Tenant VRF Config to all Leaves
# Retrieve Existing Tenant Config from configlet named "L3LS-v Tenants"
try:
  tenant_configlet = server.cvpService.getConfigletByName("L3LS-v Tenants")
  old_config = tenant_configlet["config"]
  # Add new Tenant config to existing configlet
  new_tenant_config = old_config + tenant_config
  # Generate configlet class object
  final_tenant_configlet = cvp.Configlet("L3LS-v Tenants", new_tenant_config)
  # Update configlet and return task IDs
  tasks = server.updateConfiglet(final_tenant_configlet, waitForTaskIds=True)
  print "L3LS-v Tenants Configlet updated. The following task IDs have been created. Execute them to push changes.\n"
  for task in tasks:
    print task
# If no Tenant config exists, create new configlet and apply to container named "L3LS-v Leaves"
except cvp.cvpServices.CvpError as e:
  if str(e).startswith("132801"):
    print "L3LS-v Tenants configlet does not exist. Creating...\n"
    base_tenant_configlet = cvp.Configlet("L3LS-v Tenants", tenant_config)
    server.addConfiglet(base_tenant_configlet)
    # Apply Configlet to Leafs Container
    print "\nApplying new configlet to L3LS-v Leaves Container...\n"
    base_tenant_configlet = [base_tenant_configlet]
    container_class = server.getContainer("L3LS-v Leaves")
    tasks = server.mapConfigletToContainer(container_class, base_tenant_configlet)
    print "\nConfiglet applied. The following task IDs have been created. Execute them to push changes.\n"
    for task in tasks:
      print "Task \"" + task + "\""
print ""

# Finally, apply FW edge config to border leaves
for leaf in border_leaves:
  try:
    border_configlet = server.cvpService.getConfigletByName(leaf + " Config")
    old_border_config = border_configlet["config"]
    # Add new Tenant config to existing configlet
    new_border_config = old_border_config + border_config[leaf]
    # Generate configlet class object
    final_border_configlet = cvp.Configlet(leaf + " Config", new_border_config)
    # Update configlet and return task IDs
    tasks = server.updateConfiglet(final_border_configlet, waitForTaskIds=True)
    print leaf + " Config Configlet updated. The following task ID has been created. Execute it to push changes.\n"
    for task in tasks:
      print task
    print ""
  # If no Tenant config exists, create new configlet and apply to container named "L3LS-v Leaves"
  except cvp.cvpServices.CvpError as e:
    if str(e).startswith("132801"):
      print leaf + " Config configlet does not exist. Creating...\n"
      base_border_configlet = cvp.Configlet(leaf + " Config", border_config[leaf])
      server.addConfiglet(base_border_configlet)
      # Apply Configlet to Border Leaf Device
      print "\nApplying new configlet to " + leaf + "...\n"
      base_border_configlet = [base_border_configlet]
      # Pull Device info to get class
      device_class = server._getDevicesFromInventory(leaf)
      # Apply Configlet to Device
      tasks = server.mapConfigletToDevice(device_class, base_border_configlet)
      print "\nConfiglet applied. The following task ID has been created. Execute it to push changes.\n"
      for task in tasks:
        print "Task \"" + task + "\""
      print ""