import cvp
from cvplibrary import Form
from cvplibrary import CVPGlobalVariables, GlobalVariableNames
import re

# Login to CVP API
username = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_USERNAME)
password = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_PASSWORD)
server = cvp.Cvp("localhost")
server.authenticate(username, password)

# Retrieve Form Data
vlan = Form.getFieldById("vlan").getValue()
name = Form.getFieldById("name").getValue()
vrf = Form.getFieldById("vrf").getValue()
gateway = Form.getFieldById("gateway").getValue()
mask = Form.getFieldById("mask").getValue()
jumbo = Form.getFieldById("jumbo").getValue()

# Generate Vlan Config Data
new_vlan_config = "vlan %s\n   name %s\n" % (vlan, name)

# If L3 Required, generate SVI Config
if gateway != None:
  new_svi_config = "interface Vlan%s\n" % (vlan)
  new_svi_config += "   description %s\n" % (name)
  if jumbo == "Yes":
    new_svi_config += "   mtu 9164\n"
  new_svi_config += "   vrf %s\n" % (vrf)
  new_svi_config += "   ip address virtual %s/%s\n" % (gateway, mask)
else:
  new_svi_config = ""

# Generate VNI to VLAN Mapping Config  
new_vni_config = "   vxlan vlan %s vni %s\n" % (vlan, vlan)

# Retrieve Existing Vlan Config from configlet named "Data Center Vlans"
try:
  vlan_configlet = server.cvpService.getConfigletByName("Data Center Vlans")
  old_config = vlan_configlet["config"]
  # Parse out and split exist config for sorting purposes
  old_config_list = old_config.split("!\n")
  final_vlan_list = []
  final_svi_list = []
  final_vni_list = []
  final_vlan_config = ""
  final_svi_config = ""
  final_vni_config = "interface Vxlan1\n"
  for config_section in old_config_list:
    if config_section.startswith("vlan"):
      final_vlan_list.append(config_section)
    elif config_section.startswith("interface Vlan"):
      final_svi_list.append(config_section)
    elif config_section.startswith("interface Vxlan"):
      vxlan_list = config_section.split("\n")
      for mapping in vxlan_list:
        if mapping.startswith("   vxlan"):
          final_vni_list.append(mapping + "\n")
  # Add new vlan to existing configs
  final_vlan_list.append(new_vlan_config)
  if new_svi_config != "":
    final_svi_list.append(new_svi_config)
  final_vni_list.append(new_vni_config)
  # Sort final config for visual pleasure
  final_vlan_list = sorted(final_vlan_list, key=lambda x:list(map(int, re.findall('[0-9]+(?=\n\s\s\s)', x)[0].split('/'))))
  final_svi_list = sorted(final_svi_list, key=lambda x:list(map(int, re.findall('[0-9]+(?=\n\s\s\s)', x)[0].split('/'))))
  final_vni_list = sorted(final_vni_list, key=lambda x:list(map(int, re.findall('[0-9]+(?=\svni)', x)[0].split('/'))))
  # Compile config lists into strings and concatenate for unified configlet
  for vlan in final_vlan_list:
    final_vlan_config += vlan
    final_vlan_config += "!\n"
  for svi in final_svi_list:
    final_svi_config += svi
    final_svi_config += "!\n"
  for vni in final_vni_list:
    final_vni_config += vni
  final_config = final_vlan_config + final_svi_config + final_vni_config
  # Generate configlet class object
  final_configlet = cvp.Configlet("Data Center Vlans", final_config)
  # Update configlet and return task IDs
  tasks = server.updateConfiglet(final_configlet, waitForTaskIds=True)
  print "Configlet updated. The following task IDs have been created. Execute them to push changes.\n"
  for task in tasks:
    print task
# If no Vlan config exists, create configlet and apply to container named "Leafs"
except cvp.cvpServices.CvpError as e:
  if str(e).startswith("132801"):
    print "Data Center Vlans configlet does not exist. Creating...\n"
    base_config = new_vlan_config + "!\n" + new_svi_config + "!\ninterface Vxlan1\n" + new_vni_config
    base_configlet = cvp.Configlet("Data Center Vlans", base_config)
    server.addConfiglet(base_configlet)
    # Apply Configlet to Leafs Container
    print "\nApplying new configlet to Leafs Container...\n"
    base_configlet = [base_configlet]
    container_class = server.getContainer("Leafs")
    tasks = server.mapConfigletToContainer(container_class, base_configlet)
    print "\nConfiglet applied. The following task IDs have been created. Execute them to push changes.\n"
    for task in tasks:
      print "Task \"" + task + "\""