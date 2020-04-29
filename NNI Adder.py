import cvp
from cvplibrary import Form
from cvplibrary import CVPGlobalVariables, GlobalVariableNames

# Login to CVP API
username = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_USERNAME)
password = CVPGlobalVariables.getValue(GlobalVariableNames.CVP_PASSWORD)
server = cvp.Cvp("localhost")
server.authenticate(username, password)

# Retrieve Form Data
vlan = Form.getFieldById("vlan").getValue()
name = Form.getFieldById("name").getValue()
rtr = Form.getFieldById("rtr").getValue()
iface = Form.getFieldById("iface").getValue()

# Convert rtr variable to list
rtr_list = rtr.split(",")

# Generate NNI Config Data
new_nni_config = '''vlan {vlan}
   name {name}
!
interface {iface}
   description NNI {name}
   switchport trunk allowed vlan {vlan}
   switchport mode trunk
!
router bgp 11111
   !
   vlan {vlan}
      rd auto
      route-target both {vlan}:{vlan}
      redistribute learned
!
'''.format(vlan=vlan, name=name, iface=iface)
nni_configlet_name = "{name} Config".format(name=name)

# Create NNI Configlet for Uniform deployment
print "Creating configlet for {name}...\n".format(name=name)
new_nni_configlet = cvp.Configlet(nni_configlet_name, new_nni_config)
server.addConfiglet(new_nni_configlet)
new_nni_configlet = [new_nni_configlet]

# Apply Configlet to selected Devices
print "\nApplying configlet to selected devices...\n"
device_class_dict = server._getDevicesFromInventory(rtr_list)
for router in rtr_list:
  device_class = device_class_dict[router]
  task = server.mapConfigletToDevice(device_class, new_nni_configlet)
  print "\nConfiglet applied to {router}. The following task ID has been created.\n".format(
    router=router)
  print "Task \"" + task[0] + "\""
print ""