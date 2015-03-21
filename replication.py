#!/usr/bin/python

import subprocess
import sys
import pprint
import time
import datetime
import random
import pickle
import argparse
import os

parser = argparse.ArgumentParser(description="Replicate VMs from one OVM server to another")
parser.add_argument('tag', help='OVM server side tag to snap')
parser.add_argument('local', help='Source OVM Server to read from')
parser.add_argument('remote', help='Destination OVM Server to copy to')

args=parser.parse_args()
snaptag = args.tag
sync_tag = "Snap_sync"

source_manager = "admin@%s" %(args.local)
dest_manager = "admin@%s" %(args.remote)

todaydate = time.strftime("%Y%m%d")
replnetwork = "Replication"

script_start_time = datetime.datetime.now()


servers = {}
disk_complete = []

def gatherNodeData(manager):
	vmdata = {}
	baseSSHCall = ["ssh", "-p 10000", manager ]
	listVmCall = list(baseSSHCall)
	listVmCall.append ( "list Vm" )

	vmList = subprocess.Popen(listVmCall, stdout=subprocess.PIPE)

	#Grab the VM list from the VM Server
	for line in vmList.stdout:
		if "name:" in line:
			id = line.split()[0].split(":")[1]
			name = line.split()[1].split(":")[1]

			vmdata[id] = { 'name' : name }

	# Pull the data we want from each node out of the server
	for vm in vmdata:
		if vm is "": continue
		vmdata[vm] = getNodeDetails(vm, vmdata[vm]['name'], manager)
	return vmdata

def getReplNetIp(manager, host):
	baseSSHCall = ["ssh", "-p 10000", manager ]
	getNetwork = list(baseSSHCall)
	getNetwork.append ( "show Network name=%s" %(replnetwork) )
	netDetails_out = subprocess.Popen(getNetwork, stdout=subprocess.PIPE)

	for line in netDetails_out.stdout:
		if " Vlan Segment = " in line:
			segment = line.split(None,  3)[3]

			getSegment = list(baseSSHCall)
			getSegment.append ( 'show VlanSegment name="%s"' %(segment) )
			getSegment_out = subprocess.Popen(getSegment, stdout=subprocess.PIPE)

			for line in getSegment_out.stdout:
				if host in line:
					vlanInterface = line.split()[3]

					
					getIp = list(baseSSHCall)
					getIp.append ( 'show VlanInterface id="%s"' %(vlanInterface) )
					getIp_out = subprocess.Popen(getIp, stdout=subprocess.PIPE)

					for line in getIp_out.stdout:
						if "Ip Address = " in line:
							return line.split()[3]


			



	

def getNodeDetails(id, name, manager):
	data = { 'name' : name , 'tags' : [], 'diskmap' : [] , 'disks' : [], 'pool' : "" ,  'server' : "" , 'status' : ""}
	baseSSHCall = ["ssh", "-p 10000", manager ]
	getVmCall = list(baseSSHCall)
	getVmCall.append (" show Vm id=" + id) 

	vmDetails = subprocess.Popen(getVmCall, stdout=subprocess.PIPE)


	for line in vmDetails.stdout: 
		line = line.replace("[","")
		line = line.replace("]","")
		if "tag" in line:
			data['tags'].append(line.split()[4])

		if "  Server = "in line:
			data['server'] = line.split()[3]
			servername = data['server']

			if servername in servers:
				data['pool'] = servers[servername]
			else:
				mapid = line.split()[3]
				getPoolId = list(baseSSHCall)
				getPoolId.append("show Server id=" + line.split()[2])

				serverDetail = subprocess.Popen(getPoolId, stdout=subprocess.PIPE)

				for diskline in serverDetail.stdout:
					if "Server Pool" in diskline:
						data['pool'] = diskline.split()[3]
						servers[servername] = data['pool']

		if "Status =" in line:
			data['status'] = line.split()[2]

		if "Repository =" in line:
			data['repository'] = line.split()[2]

		if "VmDiskMapping" in line:
			data['diskmap'].append(line.split()[3])

	return data

def getDisks(data, manager):
	disks = []

	baseSSHCall = ["ssh", "-p 10000", manager ]
	for id in data:
		isImg=0
		diskid = 0
		reponame = 0
		diskname = ""
		copy = 0
		size = 0

		getDiskId = list(baseSSHCall)
		getDiskId.append("show VmDiskMapping id=" + id)

		mapDetail = subprocess.Popen(getDiskId, stdout=subprocess.PIPE)

		for diskline in mapDetail.stdout:
			if "Virtual Disk Id" in diskline:
				if "img" in diskline:
					isImg=1
					diskid = diskline.split()[4]

					getDisk = list(baseSSHCall)
					getDisk.append("show VirtualDisk id=" + diskid)
					mapDetail = subprocess.Popen(getDisk, stdout=subprocess.PIPE)

					for line in mapDetail.stdout:
						if "Repository Id =" in line:
							reponame = line.split()[3]
						if "  Name =" in line:
							diskname = line.split()[2]
						if "  Max (GiB) =" in line:
							size = line.split()[3]

#		if "Sysvol" in diskname:
#			copy = 1
#		if "sysvol" in diskname:
#			copy = 1
						
		copy = 1 
		if isImg == 1:
			disks.append([diskid, reponame, diskname, copy, size])
		isImg = 0

	return disks

nodesnapped = {}

#Expire the pickle files after 10 minutes
pkl_expire_time = time.time() - 600

for file in [source_manager, dest_manager]:
	try:
		with open(file):
			st = os.stat(file)
			mtime = st.st_mtime
			if mtime < pkl_expire_time:
				os.unlink(file)
	except IOError:
		continue

try:
	with open(source_manager): 
		source_NodeData = pickle.load(open(source_manager))
	
except IOError:
#	print "Missing cache of Source OVM server data, rerunning"
	source_NodeData=gatherNodeData(source_manager)
	source_pkl= open(source_manager, "wb")
	pickle.dump(source_NodeData, source_pkl)
	source_pkl.close()

try:
	with open(dest_manager):
		dest_NodeData = pickle.load(open(dest_manager))
except IOError:
#	print "Missing cache of Destination OVM server data, rerunning"
	dest_NodeData=gatherNodeData(dest_manager)
	dest_pkl= open(dest_manager, "wb")
	pickle.dump(dest_NodeData, dest_pkl)
	dest_pkl.close()


for id in source_NodeData:
	name = source_NodeData[id]['name']
        baseSSHCall = ["ssh", "-p 10000", source_manager]

	if snaptag in source_NodeData[id]['tags']:
		method=""

		if not source_NodeData[id]['status'] == "Running":
			print "VM "+ name + " is not running, skipping"
			continue



		vmDisks = getDisks(source_NodeData[id]['diskmap'], source_manager)

		found = 0
		for destid in dest_NodeData:
			if dest_NodeData[destid]['name'] == name:
				found = 1
				tgt_destid = destid

		for i in range(len(vmDisks)):
			if found == 0:
				print "No matching node for %s found, skipping" %(name)
				continue
			else:
				if not dest_NodeData[tgt_destid]['status'] == 'Stopped':
					pprint.pprint(dest_NodeData[tgt_destid])
					print dest_NodeData[tgt_destid]['status']
					print "VM "+ name + " on destination side is running, skipping"
					continue

				dest_vmDisks = getDisks(dest_NodeData[tgt_destid]['diskmap'], dest_manager)

#				pprint.pprint(vmDisks)

				source_server = source_NodeData[id]['server']
				source_disk = vmDisks[i][0]
				source_repo = vmDisks[i][1]
				source_name = vmDisks[i][2]

				dest_server =dest_NodeData[tgt_destid]['server']
				dest_disk = dest_vmDisks[i][0]
				dest_repo = dest_vmDisks[i][1]

				print "I am going to snapshot %s on %s (%s GB) running on %s and copy it to %s" %(source_name, name, vmDisks[i][4], source_server, dest_server)


				rmReflinkDisk = [ "ssh", "root@"+source_NodeData[id]['server'], "rm -f /OVS/Repositories/%s/VirtualDisks/%s_%s.reflink" %( source_repo, name, todaydate) ]
				rmRflinkDiskOutput = subprocess.call(rmReflinkDisk, stdout = subprocess.PIPE)

				reflinkDisk = [ "ssh", "root@"+source_NodeData[id]['server'], "reflink /OVS/Repositories/%s/VirtualDisks/%s /OVS/Repositories/%s/VirtualDisks/%s_%s.reflink" %( source_repo, source_disk, source_repo, name, todaydate) ]
				reflinkDiskOutput = subprocess.call(reflinkDisk, stdout = subprocess.PIPE)

				start_time = datetime.datetime.now()
				if sync_tag in source_NodeData[id]['tags']:
					print "Starting sync of %s from %s to %s at %s" % (dest_disk, source_server, dest_server, start_time)
					copyDisk = [ "ssh", "root@"+source_NodeData[id]['server'], "rsync -B 131072 -v --progress --inplace --log-file=/var/log/replication.log -e 'ssh -o \"StrictHostKeyChecking=no\" -c arcfour' /OVS/Repositories/%s/VirtualDisks/%s_%s.reflink root@%s:/OVS/Repositories/%s/VirtualDisks/%s | tr '\r' '\n' > /tmp/rsync.out 2>&1" %( source_repo, name, todaydate, getReplNetIp(dest_manager, dest_NodeData[tgt_destid]['server']), dest_repo, dest_disk) ]
					method="Sync"
				else:
					print "Starting copy of %s from %s to %s at %s" % (dest_disk, source_server, dest_server, start_time)
					copyDisk = [ "ssh", "root@"+source_NodeData[id]['server'], "scp -o StrictHostKeyChecking=no -c arcfour /OVS/Repositories/%s/VirtualDisks/%s_%s.reflink root@%s:/OVS/Repositories/%s/VirtualDisks/%s" %( source_repo, name, todaydate, getReplNetIp(dest_manager, dest_NodeData[tgt_destid]['server']), dest_repo, dest_disk) ]
					method="Copy"

				copyDiskOutput = subprocess.call(copyDisk, stdout = subprocess.PIPE)

				end_time = datetime.datetime.now()
				delta_time = end_time - start_time
				print "Completed copy/sync of %s at %s" %(dest_disk, datetime.datetime.now())
				print "This copy took %0.1f minutes to copy %s GB for an effective rate of %s MB/s" %( (delta_time.seconds / 60), vmDisks[i][4], (float(vmDisks[i][4]) * 1024 / delta_time.seconds))
				disk_complete.append([ name, source_name, method, vmDisks[i][4], delta_time.seconds/60, (float(vmDisks[i][4]) * 1024 / delta_time.seconds), start_time, end_time])

				rmReflinkDisk = [ "ssh", "root@"+source_NodeData[id]['server'], "rm -f /OVS/Repositories/%s/VirtualDisks/%s_%s.reflink" %( source_repo, name, todaydate)  ]
				rmRflinkDiskOutput = subprocess.call(rmReflinkDisk, stdout = subprocess.PIPE)

if len(disk_complete) > 0:
	outfile = open("/tmp/replication.out", 'w')

	output_string = "Replication run for tag %s<br>\n" %(snaptag)
	output_string += "Job started at %s<br>\n" %(script_start_time)
	output_string += "<html><body>\n"
	output_string += "<table border=1><tr><th>VM Name</th><th>Disk Name</th><th>Type</th><th>Size (GB)</th><th>Time (minutes)</th><th>Effective Bandwidth(MB/s)</th><th>Start Time</th><th>End Time</th></tr>\n"

	for disk in disk_complete:
		output_string += "<tr><td>%s</td><td>%s</td><td>%s</td><td align=right>%s</td><td align=right>%0.1f</td><td align=right>%0.1f</td><td>%s</td><td>%s</td></tr>\n"%(disk[0], disk[1], disk[2], disk[3], disk[4], disk[5], disk[6].strftime("%Y-%m-%d %H:%M:%S"), disk[7].strftime("%Y-%m-%d %H:%M:%S"))

	output_string += "</table>\n"

	outfile.write(output_string)
	outfile.close()

