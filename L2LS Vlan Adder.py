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
gateway = Form.getFieldById("gateway").getValue()
mask = Form.getFieldById("mask").getValue()

# Generate Vlan Config Data
new_vlan_config = "vlan %s\n   name %s\n" % (vlan, name)

# Retrieve Existing Vlan Config from configlet named "Data Center Vlans"
try:
  vlan_configlet = server.cvpService.getConfigletByName("Data Center Vlans")
  old_config = vlan_configlet["config"]
  # Parse out and split exist config for sorting purposes
  old_config_list = old_config.split("!\n")
  final_vlan_list = []
  final_vlan_config = ""
  for config_section in old_config_list:
    if config_section.startswith("vlan"):
      final_vlan_list.append(config_section)
  # Add new vlan to existing configs
  final_vlan_list.append(new_vlan_config)
  # Sort final config for visual pleasure
  final_vlan_list = sorted(final_vlan_list, key=lambda x:list(map(int, re.findall('[0-9]+(?=\n\s\s\s)', x)[0].split('/'))))
  # Compile config lists into strings and concatenate for unified configlet
  for vlan_config in final_vlan_list:
    final_vlan_config += vlan_config
    final_vlan_config += "!\n"
  # Generate configlet class object
  final_vlan_configlet = cvp.Configlet("Data Center Vlans", final_vlan_config)
  # Update configlet and return task IDs
  tasks = server.updateConfiglet(final_vlan_configlet, waitForTaskIds=True)
  print "Configlet updated. The following task IDs have been created. Execute them to push changes.\n"
  for task in tasks:
    print task
# If no Vlan config exists, create configlet and apply to container named "Leafs"
except cvp.cvpServices.CvpError as e:
  if str(e).startswith("132801"):
    print "Data Center Vlans configlet does not exist. Creating...\n"
    base_vlan_config = new_vlan_config
    base_vlan_configlet = cvp.Configlet("Data Center Vlans", base_vlan_config)
    server.addConfiglet(base_vlan_configlet)
    # Apply Configlet to Leafs Container
    print "\nApplying new configlet to L2LS Container...\n"
    base_vlan_configlet = [base_vlan_configlet]
    container_class = server.getContainer("L2LS")
    tasks = server.mapConfigletToContainer(container_class, base_vlan_configlet)
    print "\nConfiglet applied. The following task IDs have been created. Execute them to push changes.\n"
    for task in tasks:
      print "Task \"" + task + "\""
print ""

# Parse out SVI IPs (assumes gateway + 1 and +2) if L3 will be configured
if gateway != None:
  octets = gateway.split(".")
  s1_octet = str(int(octets[3]) + 1)
  s2_octet = str(int(octets[3]) + 2)
  s1_ip = "%s.%s.%s.%s" % (octets[0],octets[1],octets[2],s1_octet)
  s2_ip = "%s.%s.%s.%s" % (octets[0],octets[1],octets[2],s2_octet)
  s1_new_svi_config = "interface Vlan%s\n" % (vlan)
  s1_new_svi_config += "   description %s\n" % (name)
  s1_new_svi_config += "   ip address %s/%s\n" % (s1_ip,mask) 
  s1_new_svi_config += "   ip virtual-router address %s\n" % (gateway)
  s2_new_svi_config = "interface Vlan%s\n" % (vlan)
  s2_new_svi_config += "   description %s\n" % (name)
  s2_new_svi_config += "   ip address %s/%s\n" % (s2_ip,mask) 
  s2_new_svi_config += "   ip virtual-router address %s\n" % (gateway)
  # Retrieve Existing SVI Config for Spine #1 from configlet named "L2LS-SPINE-1 SVIs"
  try:
    s1_svi_configlet = server.cvpService.getConfigletByName("L2LS-SPINE-1 SVIs")
    old_s1_config = s1_svi_configlet["config"]
    # Parse out and split exist config for sorting purposes
    old_s1_config_list = old_s1_config.split("!\n")
    final_s1_svi_list = []
    final_s1_svi_config = ""
    for config_section in old_s1_config_list:
      if config_section.startswith("interface"):
        final_s1_svi_list.append(config_section)
    # Add new vlan to existing configs
    final_s1_svi_list.append(s1_new_svi_config)
    # Sort final config for visual pleasure
    final_s1_svi_list = sorted(final_s1_svi_list, key=lambda x:list(map(int, re.findall('[0-9]+(?=\n\s\s\s)', x)[0].split('/'))))
    # Compile config lists into strings and concatenate for unified configlet
    for svi in final_s1_svi_list:
      final_s1_svi_config += svi
      final_s1_svi_config += "!\n"
    # Generate configlet class object
    final_s1_svi_configlet = cvp.Configlet("L2LS-SPINE-1 SVIs", final_s1_svi_config)
    # Update configlet and return task IDs
    s1_tasks = server.updateConfiglet(final_s1_svi_configlet, waitForTaskIds=True)
    print "Spine 1 SVI Configlet updated. The following task IDs have been created. Execute them to push changes.\n"
    for task in s1_tasks:
      print task
  # If no SVI config exists for Spine #1, create configlet and apply it
  except cvp.cvpServices.CvpError as e:
    if str(e).startswith("132801"):
      print "L2LS-SPINE-1 SVIs configlet does not exist. Creating...\n"
      base_s1_svi_config = s1_new_svi_config
      base_s1_svi_configlet = cvp.Configlet("L2LS-SPINE-1 SVIs", base_s1_svi_config)
      server.addConfiglet(base_s1_svi_configlet)
      # Apply Configlet to Leafs Container
      print "\nApplying new configlet to L2LS-SPINE-1...\n"
      base_s1_svi_configlet = [base_s1_svi_configlet]
      s1_device_class = server.getDevice("50:01:10:8d:12:69")
      tasks = server.mapConfigletToDevice(s1_device_class, base_s1_svi_configlet)
      print "\nSpine 1 Configlet applied. The following task ID has been created. Execute them to push changes.\n"
      for task in s1_tasks:
        print "Task \"" + task + "\""
  print ""
  
  # Retrieve Existing SVI Config for Spine #2 from configlet named "L2LS-SPINE-2 SVIs"
  try:
    s2_svi_configlet = server.cvpService.getConfigletByName("L2LS-SPINE-2 SVIs")
    old_s2_config = s2_svi_configlet["config"]
    # Parse out and split exist config for sorting purposes
    old_s2_config_list = old_s2_config.split("!\n")
    final_s2_svi_list = []
    final_s2_svi_config = ""
    for config_section in old_s2_config_list:
      if config_section.startswith("interface"):
        final_s2_svi_list.append(config_section)
    # Add new vlan to existing configs
    final_s2_svi_list.append(s2_new_svi_config)
    # Sort final config for visual pleasure
    final_s2_svi_list = sorted(final_s2_svi_list, key=lambda x:list(map(int, re.findall('[0-9]+(?=\n\s\s\s)', x)[0].split('/'))))
    # Compile config lists into strings and concatenate for unified configlet
    for svi in final_s2_svi_list:
      final_s2_svi_config += svi
      final_s2_svi_config += "!\n"
    # Generate configlet class object
    final_s2_svi_configlet = cvp.Configlet("L2LS-SPINE-2 SVIs", final_s2_svi_config)
    # Update configlet and return task IDs
    s2_tasks = server.updateConfiglet(final_s2_svi_configlet, waitForTaskIds=True)
    print "Spine 2 SVI Configlet updated. The following task IDs have been created. Execute them to push changes.\n"
    for task in s2_tasks:
      print task
  # If no SVI config exists for Spine #2, create configlet and apply it
  except cvp.cvpServices.CvpError as e:
    if str(e).startswith("132801"):
      print "L2LS-SPINE-2 SVIs configlet does not exist. Creating...\n"
      base_s2_svi_config = s2_new_svi_config
      base_s2_svi_configlet = cvp.Configlet("L2LS-SPINE-2 SVIs", base_s2_svi_config)
      server.addConfiglet(base_s2_svi_configlet)
      # Apply Configlet to Leafs Container
      print "\nApplying new configlet to L2LS-SPINE-2...\n"
      base_s2_svi_configlet = [base_s2_svi_configlet]
      s2_device_class = server.getDevice("50:01:20:63:4c:3c")
      s2_tasks = server.mapConfigletToDevice(s2_device_class, base_s2_svi_configlet)
      print "\nSpine 2 Configlet applied. The following task ID has been created. Execute them to push changes.\n"
      for task in s2_tasks:
        print "Task \"" + task + "\""
  print ""