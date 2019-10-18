from cvplibrary import Form
from cvplibrary import CVPGlobalVariables,GlobalVariableNames

hostname = Form.getFieldById( 'HOSTNAME' ).getValue()
ip = Form.getFieldById( 'IP' ).getValue()

print 'hostname ' + hostname
print '!'
print 'vrf instance management'
print '!'
print 'interface Management1'
print '   vrf management'
print '   ip address ' + ip + '/25'
print '   no lldp transmit'
print '   no lldp receive'
print '!'
print 'ip route vrf management 0.0.0.0/0 10.2.244.1'
print '!'
print 'no ip routing vrf management'
print '!'
print 'management api http-commands'
print '   no shutdown'
print '   !'
print '   vrf management'
print '      no shutdown'