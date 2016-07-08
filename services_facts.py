#!/usr/bin/python

import os, re, platform, json
from parse import compile
import StringIO
from subprocess import Popen, PIPE
import subprocess
import glob

DOCUMENTATION = '''
---
module: services_facts; tested on Ubuntu 10,12,14,16 and CentOS 5,6,7
author:
    - "Domenico Caruso" domenico.caruso@de.clara.net

short_description: Provide facts regarding services: whether they are boot enabled and/or running at the momement;
moreover it provides what ports are listening to and what connections are established

description: Unfortunately every system has a different init daemon and services are sometimes differtly managed: some are native to the init daemon some are backwards compatibility. Moreover, the same command can have a different output, e.g., service --status-all works on both Ubuntu and CentOS but the output is very different.

'''

EXAMPLES = '''
Example output:
    "clara_services_established": {
        "nscd": {
            "389": "1.2.3.4"
        },
        "sshd:": {
            "41478": "10.0.2.2"
        .
        .
        .

    "clara_services_init": {
        "accounts-daemon_service": "enabled",
        "acpid_service": "enabled",
        "apache-htcacheclean_service": "disabled",
        "apache2_service": "enabled",
        "apport-forward@_service": "static",
        "apport_service": "enabled",
        "apt-daily_service": "static",
        "atd_service": "enabled",
         .
         .
         .

    "clara_services_status": {
        "accounts-daemon_service": "active",
        "acpid_service": "active",
        "apache-htcacheclean_service": "active",
        "apache2_service": "active",
        "apparmor_service": "active",
        "apport_service": "active",
        "apt-daily_service": "inactive",
        "atd_service": "active",
         .
         .
         .

    "clara_services_listening": {
        "apache2": {
            "80": "::"
        },
        "bacula-fd": {
            "9102": "127.0.0.1"
        },
        "exim4": {
            "25": "::1"
        },
        .
        .
        .
'''

def _get_command_output_lines(cmd, parse_string):
    lines = []

    stdout = Popen(cmd, stdout=PIPE).communicate()[0]
    stream = StringIO.StringIO(stdout)
    parser = compile(parse_string)

    for line in stream:
        res = parser.parse(line)
        if not res:
            continue
        lines.append(res.named)
    return lines

# here we get info about enabled/disabled services
def parse_init():
    result = {}
    lines = []

    # SYSTEMD gather facts, this works with Ubuntu 16 and CentOS 7 only
    if platform.dist()[2] == 'xenial' or platform.dist()[1].split('.')[0] == '7':
        lines = _get_command_output_lines(['systemctl', 'list-unit-files', '--type=service'], '{key} {value}')
        for named in lines:
            result[named['key'].replace('.', '_').lower()] = named['value'].strip()


    # SYSTEM V gather facts for CentOS
    if ("centos" in platform.dist()[0].lower() or "redhat" in platform.dist()[0].lower()) and platform.dist()[1].split('.')[0] >= '6':
       service1 = subprocess.Popen(['chkconfig', '--list'], stdout=PIPE).communicate()[0]
       stream = StringIO.StringIO(service1)
       for line in stream:
           arr = re.split(r'[0-9]:',line)
           if arr[3].strip("\t") == arr[4].strip("\t") == arr[5].strip("\t") == arr[6].strip("\t") == "off":
              result [ arr[0].strip("\t").strip().replace('.', '_').lower()+'_service' ] = "disabled"
           else:
              result [ arr[0].strip("\t").strip().replace('.', '_').lower()+'_service'] = "enabled"
    elif platform.dist()[1].split('.')[0] == '5':
       service1 = subprocess.Popen(['sudo','/sbin/chkconfig', '--list'], stdout=PIPE).communicate()[0]
       stream = StringIO.StringIO(service1)
       for line in stream:
           arr = re.split(r'[0-9]:',line)
           if arr[3].strip("\t") == arr[4].strip("\t") == arr[5].strip("\t") == arr[6].strip("\t") == "off":
              result [ arr[0].strip("\t").strip().replace('.', '_').lower()+'_service' ] = "disabled"
           else:
              result [ arr[0].strip("\t").strip().replace('.', '_').lower()+'_service'] = "enabled"

    # SYSTEM V gather facts, this works on Ubuntu
    if platform.dist()[0] == 'Ubuntu':
       service_files = glob.glob("/etc/rc2.d/*")
       stream = []
       for l in service_files:
           filename_firstchar =  os.path.basename(l)[0]
           if filename_firstchar == 'S':
              service_name = re.split(r'[S][0-9]+', l)[1].replace('.', '_').lower() + '_service'
              result[ service_name ] = "enabled"
           elif filename_firstchar == 'K':
               service_name = re.split(r'[K][0-9]+', l)[1].replace('.', '_').lower() + '_service'
               result[ service_name ] = "disabled"
           else:
              continue
                                  
    # UPSTART gather facts, for all Ubuntu and CentOS/RedHat 6
    if platform.dist()[0] == 'Ubuntu' or platform.dist()[1].split('.')[0] == '6':
        service1 = subprocess.Popen(['grep', '-i','runlevel'] + glob.glob("/etc/init/*"), stdout=PIPE).communicate()[0]
        stream = StringIO.StringIO(service1)
        for named in stream:
             if "#" not in named and "start on" in named and (re.search(r'[2-5]',named)):
                service_name = str(named).replace("/"," ").split()[2].split(".")[0].replace('.', '_').lower()+'_service'
                result[ service_name ] = "enabled"
             elif "#" not in named and "start on" in named and not (re.search(r'[2-5]',named)):
                service_name = str(named).replace("/"," ").split()[2].split(".")[0].replace('.', '_').lower()+'_service'
                result[ service_name ] = "disabled"

    return result


# here we get the info about running/stopped services
def parse_status():
    result = {}
    lines = []

    # SYSTEMD gather facts, this works with Ubuntu 16 and CentOS 7 only
    if platform.dist()[2] == 'xenial' or platform.dist()[1].split('.')[0] == '7':
        service1 = subprocess.Popen(['systemctl', 'list-units', '--all', '--type=service', '--plain', '--no-legend'], stdout=PIPE)
        stream = StringIO.StringIO(service1.communicate()[0])
        for named in stream:
            service_name = named.split()[0]
            service_status = named.split()[2]
            result[ service_name.replace('.', '_').lower() ] = service_status.strip()


    # SYSTEM V gather facts, this works on all Ubuntu versions
    if platform.dist()[0] == 'Ubuntu':
        service1 = subprocess.Popen(['service', '--status-all'], stdout=PIPE, stderr=subprocess.STDOUT).communicate()[0]
        stream = StringIO.StringIO(service1)
        for named in stream:
            service_name = named.split()[3].replace('.', '_')+'_service'
            service_status = named.split()[1].strip().replace('+','active').replace('-','inactive').replace('?','unknown')
            result[service_name] = service_status


    # SYSTEM V gather facts, for CentOS
    if ("centos" in platform.dist()[0].lower() or "redhat" in platform.dist()[0].lower()) and platform.dist()[1].split('.')[0] >= '6':
        service1 = subprocess.Popen(['service', '--status-all'], stdout=PIPE)
        service2 = subprocess.Popen(['grep', 'running\|stopped'], stdin=service1.stdout,stdout=PIPE).communicate()[0]
        stream = StringIO.StringIO(service2)
        for named in stream:
            service_name = named.split()[0].replace('.', '_')+'_service'
            if "is" in named:
               service_status = named.split(" is ")[1].replace(".","").replace(" ","_").strip().replace('not_running','inactive').replace('stopped','inactive').replace('running','active')
               result [ service_name ] = service_status
            else:
               continue
    elif platform.dist()[1].split('.')[0] == '5': 
        service1 = subprocess.Popen(['sudo', '/sbin/service', '--status-all'], stdout=PIPE)
        service2 = subprocess.Popen(['grep', 'running\|stopped'], stdin=service1.stdout,stdout=PIPE).communicate()[0]
        stream = StringIO.StringIO(service2)
        for named in stream:
            service_name = named.split()[0].replace('.', '_')+'_service'
            if "is" in named:
               service_status = named.split(" is ")[1].replace(".","").replace(" ","_").strip().replace('not_running','inactive').replace('stopped','inactive').replace('running','active')
               result [ service_name ] = service_status
            else:
               continue

    # UPSTART gather facts, it is not supported on Ubuntu 16 and Centos 5,7
    if (platform.dist()[2] != 'xenial' and platform.dist()[0] == 'Ubuntu') or platform.dist()[1].split('.')[0] == '6':
        service1 = subprocess.Popen(['initctl', 'list'], stdout=PIPE).communicate()[0]
        stream = StringIO.StringIO(service1)
        for named in stream:
            service_name = str(named.split(",")[0]).replace(" (","_(").split()[0].replace('.', '_')+'_service'
            service_status = str(named.split(",")[0]).replace(" (","_(").split()[1].strip().replace('start/running','active').replace('stop/waiting','inactive')
            result [ service_name ] = service_status

    return result


def parse_listening():
    result = {}
    service1 = subprocess.Popen(['netstat', '-tulnep'], stdout=PIPE).communicate()[0]
    stream = StringIO.StringIO(service1)

    for line in stream:
        var = ['tcp','udp']
        for a in var:
            if re.search(a,line.split()[0]):
               if re.search('tcp',line.split()[0]): 
                   service_name = line.split()[8].split("/")[1]
               if re.search('udp',line.split()[0]):
                   service_name = line.split()[7].split("/")[1]
               local_ip = line.split()[3].rsplit(':',1)[0]
               local_port = line.split()[3].rsplit(':',1)[1]
               if service_name not in result:
                  result[service_name] = {}
               result[service_name][local_port] = local_ip  

    return result

def parse_established():        
    result = {}
    service1 = subprocess.Popen(['netstat', '-tnep'], stdout=PIPE).communicate()[0]
    stream = StringIO.StringIO(service1)

    for line in stream:
        if not (re.search('tcp',line.split()[0]) and re.search('ESTA',line.split()[5])) : continue
        else:
           try:
              service_name = line.split()[8].split("/")[1]
              foreign_ip = line.split()[4].rsplit(':',1)[0]
              foreign_port = line.split()[4].rsplit(':',1)[1]
              if service_name not in result:
                 result[service_name] = {}
              result[service_name][foreign_port] = foreign_ip
           except:
               continue

    return result

established = {}
established['established'] = parse_established()
listening = {}
listening['listening'] = parse_listening()
status = {}
status['status'] = parse_status()
init = {}
init['init'] = parse_init()
with open('risultato.txt','w') as outfile:
     json.dump(init,outfile,indent=1)
with open('risultato.txt','aw') as outfile:
     json.dump(status,outfile,indent=1)
with open('risultato.txt','aw') as outfile:
     json.dump(established,outfile,indent=1)
with open('risultato.txt','aw') as outfile:
     json.dump(listening,outfile,indent=1)
