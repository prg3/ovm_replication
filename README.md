# ovm_replication
Oracle VM Replication Scripts

Simple python script that uses filesystem snapshots and scp to replicate OVM guests between OVM installations. This is a completly backend storage agnostic replciation solution, that does not require matching UUIDs of the Managers.

Installation
____________
* Setup SSH keys between OVM Managers with authorized_keys
* Copy the public ssh key into each of the ovm hosts ~root/.ssh/authorized_keys
* Copy repl_runner.sh and replication.py to /usr/bin on the source manager
* Modify repl_runner.sh to adjust FROM and TO fields
* Setup Tags in your OVM Manager
* Assign Tags to gusts

Usage
_____
This si intended to be run via cron

5 0 * * * root /usr/bin/repl_runner.sh sourceIp destinationIp

You can run the python script directly:
 replication.py <Snapname> <Local Manager> <Remote Manager>

Predefined Tags
_______________

* Snap_monthy_1 through Snap_monthly_5 - Runs a Snapshot on the Nth Saturday of the month
* Snap_sunday, Snap_monday through Snap_friday - Runs a Shapshot on the specific day of the week
* Snap_sync - experimental (i.e. it didn't work right for me so I stopped using it) uses rsync rather than scp to copy the VM, which should cause less network usage

Notes
_____

After a reboot or restart of the OVM Manager, you will need to manually ssh to each of the managers and enter in your admin login credentials:
Specifically, running from the host:

* ssh -p 10000 admin@sourceIp
* ssh -p 10000 admin@destinationIp

* Tested on OVM 3.2.8

* arcfour encryption was used for performance.

* Note that above the job runs at 5am at system local time.

