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
tenant = Form.getFieldById("tenant").getValue()
gateway = Form.getFieldById("gateway").getValue()
mask = Form.getFieldById("mask").getValue()

# Generate Vlan Config Data
new_vlan_config = "vlan %s\n   name %s\n" % (vlan, name)
new_vni_config = "   vxlan vlan %s vni %s" % (vlan, vlan)
new_macvrf_config = "   vlan %s\n" % (vlan)
new_macvrf_config += "      rd auto\n"
new_macvrf_config += "      route-target both %s:%s\n" % (vlan, vlan)
new_macvrf_config += "      redistribute learned\n   "
if gateway != None:
  new_svi_config = "interface Vlan%s\n" % (vlan)
  new_svi_config += "   description %s\n" % (name)
  new_svi_config += "   vrf %s\n" % (tenant)
  new_svi_config += "   ip address virtual %s/%s\n" % (gateway, mask)

# Retrieve Existing Tenant Config from configlet named "L3LS-v Tenant Vlans"
try:
  tenant_configlet = server.cvpService.getConfigletByName("L3LS-v Tenant Vlans")
  old_config = tenant_configlet["config"]
  # Parse out and split exist config for sorting purposes
  old_config_list = old_config.split("!\n")
  final_vlan_list = []
  final_svi_list = []
  final_vni_list = []
  final_macvrf_list = []
  final_vlan_config = ""
  final_svi_config = ""
  final_vni_config = "interface Vxlan1\n"
  final_macvrf_config = "router bgp 65002\n   !\n"
  for config_section in old_config_list:
    if config_section.startswith("vlan"):
      final_vlan_list.append(config_section)
    elif config_section.startswith("interface Vlan"):
      final_svi_list.append(config_section)
    elif config_section.startswith("interface Vxlan"):
      old_vni_config = config_section[17:]
      old_vni_list = old_vni_config.split("\n")
      for vni_mapping in old_vni_list:
        final_vni_list.append(vni_mapping)
      final_vni_list.pop()
    elif config_section.startswith("   vlan"):
      final_macvrf_list.append(config_section)
  # Add new vlan to existing configs
  final_vlan_list.append(new_vlan_config)
  # Sort final config for visual pleasure
  final_vlan_list = sorted(final_vlan_list, key=lambda x:list(map(int, re.findall('[0-9]+(?=\n\s\s\s)', x)[0].split('/'))))
  # Compile config lists into strings and concatenate for unified configlet
  for vlan_config in final_vlan_list:
    final_vlan_config += vlan_config
    final_vlan_config += "!\n"
  # Add new SVI to existing configs
  if gateway != None:
    final_svi_list.append(new_svi_config)
  # Sort final config for visual pleasure
  final_svi_list = sorted(final_svi_list, key=lambda x:list(map(int, re.findall('[0-9]+(?=\n\s\s\s)', x)[0].split('/'))))
  # Compile config lists into strings and concatenate for unified configlet
  for svi_config in final_svi_list:
    final_svi_config += svi_config
    final_svi_config += "!\n"
  # Add new VNI to existing configs
  final_vni_list.append(new_vni_config)
  # Sort final config for visual pleasure
  final_vni_list = sorted(final_vni_list, key=lambda x:list(map(int, re.findall('[0-9]+(?=\s)', x)[0].split(' vni '))))
  # Compile config lists into strings and concatenate for unified configlet
  for vni_config in final_vni_list:
    final_vni_config += vni_config
    final_vni_config += "\n"
  final_vni_config += "!\n"
  # Add new MAC-VRF to existing configs
  final_macvrf_list.append(new_macvrf_config)
  # Sort final config for visual pleasure
  final_macvrf_list = sorted(final_macvrf_list, key=lambda x:list(map(int, re.findall('[0-9]+(?=\n\s\s\s)', x)[0].split('/'))))
  # Compile config lists into strings and concatenate for unified configlet
  for macvrf_config in final_macvrf_list:
    final_macvrf_config += macvrf_config
    final_macvrf_config += "!\n"
  # Combine all configlet sections
  final_tenant_config = final_vlan_config + final_svi_config + final_vni_config + final_macvrf_config
  # Generate configlet class object
  final_tenant_configlet = cvp.Configlet("L3LS-v Tenant Vlans", final_tenant_config)
  # Update configlet and return task IDs
  tasks = server.updateConfiglet(final_tenant_configlet, waitForTaskIds=True)
  print "Configlet updated. The following task IDs have been created. Execute them to push changes.\n"
  for task in tasks:
    print task
# If no Vlan config exists, create configlet and apply to container named "L3LS-v Leaves"
except cvp.cvpServices.CvpError as e:
  if str(e).startswith("132801"):
    print "L3LS-v Tenant Vlans configlet does not exist. Creating...\n"
    if gateway != None:
      base_tenant_config = new_vlan_config + "!\n" + new_svi_config + "!\n" 
      base_tenant_config += "interface Vxlan1\n" + new_vni_config + "\n!\n"
      base_tenant_config += "router bgp 65002\n   !\n" + new_macvrf_config
    else:
      base_tenant_config = new_vlan_config + "!\n"
      base_tenant_config += "interface Vxlan1\n" + new_vni_config + "!\n"
      base_tenant_config += "router bgp 65002\n   !\n" + new_macvrf_config
    base_tenant_configlet = cvp.Configlet("L3LS-v Tenant Vlans", base_tenant_config)
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