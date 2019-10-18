import cvp
from cvplibrary import Form
from cvplibrary import CVPGlobalVariables, GlobalVariableNames
import re
import sys

# Login to CVP API
username = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_USERNAME)
password = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_PASSWORD)
server = cvp.Cvp("localhost")
server.authenticate(username, password)

# Retrieve Form Data
int_type = Form.getFieldById("int_type").getValue()
single_switch = Form.getFieldById("single_switch").getValue()
single_int = Form.getFieldById("single_int").getValue()
pair = Form.getFieldById("pair").getValue()
mlag_id = Form.getFieldById("mlag_id").getValue()
mlag_int = Form.getFieldById("mlag_int").getValue()
desc = Form.getFieldById("desc").getValue()
mode = Form.getFieldById("mode").getValue()
access_vlan = Form.getFieldById("access_vlan").getValue()
trunk_vlans = Form.getFieldById("trunk_vlans").getValue()
native_vlan = Form.getFieldById("native_vlan").getValue()

# Pull in corresponding port configlets for concatenation and collision checks
if int_type == "Stand-alone":
  try:
    pair = single_switch[:-1] + "A / B"
    mlag_configlet = server.cvpService.getConfigletByName(pair + " MLAGs")
    old_mlag_config = mlag_configlet["config"]
    # Parse out and split existing mlag config for collision checking
    old_mlag_list = old_mlag_config.split("!\n")
    # Check if new port exists in mlag configlet
    for port in old_mlag_list:
      if port.startswith("interface Ethernet" + single_int):
        print "Specified Interface is already configured for as MLAG Member interface. Verify current config and settings"
        print "Exiting script"
        sys.exit()
  except cvp.cvpServices.CvpError as mlag_error:
    if str(mlag_error).startswith("132801"):
      print "No MLAG Configlet currently exists. Assuming no overlap and continuing...\n"
  try:
    port_configlet = server.cvpService.getConfigletByName(single_switch + " Interfaces")
    old_port_config = port_configlet["config"]
    # Parse out and split existing config for sorting and collision checking
    old_port_list = old_port_config.split("!\n")
    # Check if new port exists in configlet
    for port in old_port_list:
      if port.startswith("interface Ethernet" + single_int):
        if mode == "Access":
          print "Specified Interface is already configured for mode access. Verify current config and settings"
          print "Exiting script"
          sys.exit()
        elif mode == "Trunk":
          print "Specified Interface is configured as a trunk. Vlans will be added to existing trunk.\n"
  except cvp.cvpServices.CvpError as single_error:
    if str(single_error).startswith("132801"):
      print "No Stand-alone Interfaces Configlet currently exists. One will be created...\n"
elif int_type == "MLAG":
  single_a = pair[:-4]
  single_b = pair[:-5] + "B"
  try:
    port_a_configlet = server.cvpService.getConfigletByName(single_a + " Interfaces")
    old_port_a_config = port_a_configlet["config"]
    # Parse out and split existing config for sorting and collision checking
    old_port_a_list = old_port_a_config.split("!\n")
    # Check if new port exists in configlet
    for port in old_port_a_list:
      if port.startswith("interface Ethernet" + mlag_int):
        print "Specified Interface is already configured for as Stand-alone interface. Verify current config and settings"
        print "Exiting script"
        sys.exit()
  except cvp.cvpServices.CvpError as single_a_error:
    if str(single_a_error).startswith("132801"):
      print "No Switch A Configlet currently exists. Assuming no overlap and continuing...\n"
  try:
    port_b_configlet = server.cvpService.getConfigletByName(single_b + " Interfaces")
    old_port_b_config = port_b_configlet["config"]
    # Parse out and split existing config for sorting and collision checking
    old_port_b_list = old_port_b_config.split("!\n")
    # Check if new port exists in configlet
    for port in old_port_b_list:
      if port.startswith("interface Ethernet" + mlag_int):
        print "Specified Interface is already configured for as Stand-alone interface. Verify current config and settings"
        print "Exiting script"
        sys.exit()
  except cvp.cvpServices.CvpError as single_b_error:
    if str(single_b_error).startswith("132801"):
      print "No Switch B Configlet currently exists. Assuming no overlap and continuing...\n"
  try:
    mlag_configlet = server.cvpService.getConfigletByName(pair + " MLAGs")
    old_mlag_config = mlag_configlet["config"]
    # Parse out and split existing mlag config for collision checking
    old_mlag_list = old_mlag_config.split("!\n")
    # Check if new port exists in mlag configlet
    for port in old_mlag_list:
      if port.startswith("interface Ethernet" + mlag_int):
        # SPLIT MLAG ID FOR COMPARISON?
        print "yay"
  except:
    print "yay"
# Generate Port Configs
if int_type == "Stand-alone":
  new_port_config = "interface Ethernet%s\n" % (single_int)
  new_port_config += "   description %s\n" % (desc)
  if mode == "Access":
    new_port_config += "   switchport access vlan %s\n" % (access_vlan)
  else:
    if native_vlan != None:
      new_port_config += "   switchport trunk native vlan %s\n" (native_vlan)
    new_port_config += "   switchport trunk allowed vlan %s\n" (trunk_vlans)
    new_port_config += "   switchport mode trunk"
  new_port_config += "   spanning-tree portfast\n"
else:
  new_mlag_config = "interface Port-Channel%s\n" % (mlag_id)
  new_mlag_config += "   description %s\n" % (desc)

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