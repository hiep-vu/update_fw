#!/usr/local/bin/python2.7
'''
Nutanix
Program Name: update_nic_fw.py

This utility helps in checking the NIC firmware version on the model. If the \
firmware is outdated, it will update with the preferred one from the file: \
"fw_config.py". This utility saves all logs into pre-existing directory: \
uut_logs. This script also has the option to force the update.

Prerequisites:
    - This module is tested on Python 2.7.15 and is compatible with python
      2.7 or later.

Usage:
    $ ./update_nic_fw.py -h
    $ python update_nic_fw.py -h
    usage: update_nic_fw.py [-h] [-l LOG] [--username USERNAME] \
                     [--password PASSWORD] [--ip IP] \
                     [-m model] [-p part] [-v version to update]

    NIC Firmware Update

    optional arguments:
      -h, --help            Show this help message and exit
      -l LOG, --log LOG     Specify the log filename to be saved as
      --username USERNAME   username
      --password PASSWORD   password
      --ip IP               Destination IP to collect information on
      -m                    Model
      -p                    Part 
      -v                    NIC path/version to flash

Examples:
    Updates the NIC on the local system without specifying a file:
        python update_nic_fw.py
        or
        ./update_nic_fw.py

    Updates the NIC on the local system with the mother board "NX-8036-G6" with \
    specific nic part "AOC-MTG_I2TM-NI22" firmware version "0x80000aee":
        python update_nic_fw.py -m NX-8036-G6 -p AOC-MTG-I2TM-NI22 -v 0x80000aee
        or
        ./update_nic_fw.py -m NX-8036-G6 -p AOC-MTG-I2TM-NI22 -v 0x80000aee

    Updates NIC firmware on the remote system with the ip=192.168.2.123 \
        python update_nic_fw.py --ip=192.168.2.123
        or
        ./update_nic_fw.py --ip=192.168.2.123

    Updates the NIC on the remote ip=192.168.2.123 with the motherboard \
    "NX-8036-G6" and with the specific nic part "AOC-MTG_I2TM-NI22" firmware version 0x80000aee:
        python update_nic_fw.py --ip=192.168.2.123 -m NX-8036-G6 -p AOC-MTG-I2TM-NI22 -v 0x80000aee
        or
        ./update_nic_fw.py --ip=192.168.2.123 -m NX-8036-G6 -p AOC-MTG-I2TM-NI22 -v 0x80000aee

    Specifies the file name for the log file containing the retrieved \
    information:
        python update_nic_fw.py --ip=192.168.2.123 -l=sn123_update_nic_fw.log
        or
        ./update_nic_fw.py --log=sn123_update_nic_fw.log

    Specifies the file name for the JSON file containing the retrieved \
    information:
        python update_nic_fw.py --ip=192.168.2.123 -j=node_sn.json
        or
        ./update_nic_fw.py --json=node_sn.json

'''
import json
import os
import re
import sys
import time
import argparse
import logging

# Import your package (if any) below
import import_me_first

from pexpect.exceptions import TIMEOUT
from lib.connection import Connection
from lib.dec import time_elapsed
import fw_config as NIC

logging.basicConfig(filename="debug_nic_fw.log", level=logging.DEBUG)
#logging.basicConfig(level=logging.DEBUG)

this_filename = os.path.basename(__file__).split('.')[0]

def parse_args():
    ''' This function creates a parser object and adds the arguments and
        information regarding the arfument to the parser object. It then
        returns the parsed arguments
    '''
    parser = argparse.ArgumentParser(
        description='This parser gets all input options to do the NIC update')

    # Add arguments
    parser.add_argument(
        '-l', '--log',
        help='Specify the log filename to be saved as',
            default='{0}.log'.format(os.path.basename(__file__).split('.')[0]))
    parser.add_argument(
        '--username', required=False,

        # Default username for the PXE server
        help='username', default='root')
    parser.add_argument(
        '--password', required=False,

        # Default password for the PXE server
        help='password', default='nutanix/4u')
    parser.add_argument(
        '--ip', required=False,
        help='Destination IP to collect information from', default='localhost')
    parser.add_argument(
        '-m', '--model', type=str,
        help='model name to update', required=False)
    parser.add_argument(
        '-p', '--part', type=str,
        help='file name to update', required=False, nargs='+')
    parser.add_argument(
        '-v', '--version', type=str,
        help='firmware version to update', required=False, nargs='+')
    args = parser.parse_args()
    return args

''' ----------------------------- GET FRU INFO ------------------------------'''
def get_fru_info(conn, verbose=False):
    ''' This function gets and returns the model from the chasis
    '''
    fru = {}

    # Get FRU info if it does not exist
    conn.sendline('ipmitool fru', conn.PROMPT)
    if conn.output:
        for line in conn.output.split('\n')[1:]:
            if ' : ' in line:
                k, v = line.split(' : ', 1)
                fru[k.strip()] = v.strip()
    else:
        logging.error('ERROR: ipmitool fru command returns nothing!')
        sys.exit(1)

    if verbose:
        logging.debug(json.dumps(fru, indent=4))
    return fru

''' ------------------------- GET ETHER INTERFACES --------------------------'''

def get_enp_interface(conn, verbose=False):
    """ This function checks the motherboard to find all NIC installed. It
        returns a list of all interface ports.
    """
    interface = []
    conn.sendline('ip addr show | grep -Po "enp\d+\w+\d+" | uniq | sort -n',
                   conn.PROMPT)
    if conn.output:
        logging.debug("conn %s " %conn.output)
        interface = re.findall(r'\enp\w+[f][0$]', conn.output)

    if verbose:
        logging.debug(json.dumps(interface, indent=4))

    return interface

'''------------------------------- Sub System ------------------------------'''

def get_sub_system_from_eth(conn, dev, verbose=False):
    """ This function finds Subsystem that is SUBVENDOR:SUBDEVICE
    """
    cmd='ethtool -i %s | grep -i bus | grep -Po "[0-9a-f]+\:[0-9a-f]+\.[0-9a-f]+"' %dev
    conn.sendline(cmd, conn.PROMPT)
    if conn.output:
        logging.debug("conn output %s " %conn.output)
        bus = re.search(r'[0-9a-f]+\:\w+\.\d+', conn.output)
        bus = bus.group()

    if verbose:
        logging.debug(json.dumps(bus, indent=4))

    cmd="lspci -s %s -vn" %bus
    conn.sendline(cmd, conn.PROMPT)
    if conn.output:
       logging.debug("conn output %s " %conn.output)
       sub_system = re.search(r'\Subsystem:\s+[0-9a-f]{4}\:[0-9a-f]{4}',
               conn.output)
       sub_system = re.search(r'[0-9a-f]+\:[0-9a-f]{4}', sub_system.group())
       logging.debug("subsys %s " %sub_system.group())

    if verbose:
        logging.debug(json.dumps(sub_system, indent=4))

    return sub_system.group()

'''----------------------------- GET DEVICE FIRMWARE ------------------------'''

#@time_elapsed
def get_fw_from_eth(conn, dev, verbose=False):
    """ This function finds the firmware version for the device
    """
    cmd="ethtool -i  %s | grep -i firmware | cut -d: -f2" %dev
    conn.sendline(cmd, conn.PROMPT)
    if conn.output:
        logging.debug(conn.output)
        fw = re.search(r'[0x]+\d+[0-9a-f]+', conn.output)

    if verbose:
        logging.debug(json.dumps(firmware, indent=4))

    return fw.group()

''' ------------------------- Check DEVICE FW Acceptable --------------------'''

#@time_elapsed
def is_fw_acceptable(conn, nic_baseboard, nic_version, verbose=False):
    """ This function checks if the firmware reading from the nic baseboard is
        acceptable. if the firmware is in the list of acceptable firmwares, it
        returns True.
    """

    if (nic_version in NIC.NIC_FW_ACCEPTABLE[nic_baseboard]):
        logging.info("NIC firmware version: %s is acceptable" %nic_version)
        return True
    else:
        logging.info("NIC firmware: %s is not acceptable update required" %nic_version)
        if verbose:
            logging.debug(json.dumps(nic_version, indent=4))

        return False

''' ----------------------- Check NIC FW Update Conflict --------------------'''

#@time_elapsed
def is_update_conflict(conn, nic_part_number, nic_version, prefer_nic_version, verbose=False):
    """ This function checks if the NIC version on the board will be in conflict
        when we update to the preferred one. if the update causes a conflict,
        return True
    """
    if (nic_version in NIC.NIC_FW_CONFLICT[(nic_part_number, prefer_nic_version)]):
        logging.error("FAIL:NIC:UPDATE:Detected=" + str(nic_version) +
                ":Couldn't update to the prefer version")
        logging.debug("NIC version updated from version: % to version: % will"
                "cause a conflict" %(nic_version, prefer_nic_version))
        return True
    else:
        logging.info("NIC current firmware %s is not conflicted" %nic_version)
        return False
""" ----------------------- update_process ----------------------------------"""
"""

./nvmupdate64e -u -sv -l -c nvmupdate.cfg
[root@localhost AOC]# ./nvmupdate64e -u -sv -l -c nvmupdate.cfg

Intel(R) Ethernet NVM Update Tool
NVMUpdate version 1.29.3.2
Copyright (C) 2013 - 2017 Intel Corporation.

Config file read.
Config file doesn't have any OROM components specified for device 'Intel X550 Adapter'. 
Tool will use current device's combo set for the OROM update.
Inventory
[00:024:00:00]: Intel(R) Ethernet Controller X550-T2
        Flash inventory started
        Shadow RAM inventory started
        Shadow RAM inventory finished
        Flash inventory finished
        OROM inventory started
        OROM inventory finished
[00:024:00:01]: Intel(R) Ethernet Controller X550-T2
        Device already inventoried.
Update
[00:024:00:00]: Intel(R) Ethernet Controller X550-T2
        Flash update started
|======================[100%]======================|
        NVM image verification skipped
        Flash update successful
        OROM: Requested image version is older than on the NIC - skipping update
Power Cycle is required to complete the update process.
[root@localhost AOC]#

# Require reboot
"""
'''--------------------------do_fw_update-------------------------'''
#@time_elapsed
def do_fw_update(conn, file_name):
    ''' This function gets the nic file name and performs the update.
    '''
    # Check if the update files exists.
    conn.sendline('ls '+file_name, "#", timeout=10)
    conn.output = conn.output.split()
    conn.output = conn.output[1]

    if conn.output != file_name:
        logging.error ("File %s is not found " %file_name)
        logging.debug(conn.output)
        sys.exit(1)
    else:
        logging.info("Found file do firmware update")

    logging.debug("Update file @location %s " %(file_name))
    path, file_name = os.path.split(file_name)
    logging.debug("Path: %s file: %s" %(path, file_name))
    CMD = "%s/nvmupdate64e -a %s -u -sv -l -c %s " %(path, path, file_name)
    # Update Complete, Please wait for NIC reboot, about 1 or 2 mins
    conn.sendline(CMD , "#", timeout=200)
    if conn.output:
        logging.debug(conn.output)
        update = re.search('Power (.*) required', conn.output)
        if update:
            logging.debug(update.group())
            logging.info("The UUT payload power will require to be power cycled.")
            print("UUT requires the node power cycle!")
        else:
            logging.info("UUT does not require an update")
            print("UUT does not required update!")

''' --------------------------- NIC Update Process --------------------------'''
#@time_elapsed
def check_update_process(conn, part_number, fw_version):
    """ This function checks if the current firmware requires an update, and if
        it is updatable. If the current firmware is updatable, return True. The
        function also returns the file name to update.
    """

    try:
        prefer_nic_version = NIC.NIC_FW_PREFER[part_number]
        logging.debug("preferred nic version: %s" %(prefer_nic_version))
        file_name = NIC.NIC_FW_FILES[(part_number, prefer_nic_version)]
        logging.debug(file_name)
    except KeyError, e:
        logging.error("The version %s is not supported" %part_number)
        exit(1)

    # First check for the update requirement
    if fw_version == prefer_nic_version:
        logging.info("Current NIC version " + fw_version + " is matched with the prefer")
        # TESTING - Comment out the return to ignore the prefer version
        return(False, file_name)
    else:
        logging.debug("Version mismatch. Next, checking version in " +
                "acceptable list")

    # Second check the current firmware is acceptable
    if is_fw_acceptable(conn, part_number, fw_version):
        logging.debug("Version is acceptible")
        logging.info("Current NIC version "+fw_version+" is acceptable")
        # TESTING - Comment out the acceptable to update with the new version
        return(False, file_name)
    else:
        logging.debug("Version is not acceptable. An update is required.")
        logging.info("Current NIC.NIC version "+fw_version+" is outdated/ " +
                "un-qualified. Running NIC update process:")

    # Third check if the update is conflict
    if is_update_conflict(conn, part_number, fw_version, prefer_nic_version):
        logging.error("Update causes a conflict. Exiting.")
        exit(1)
    else:
        logging.debug("Update does not cause a conflicted. Updating")

    return(True, file_name)

'''-------------------------------------------------------------------------'''
def check_support_process(conn, model, part, version):
    """ This function checks if the foced update option is available. If the
        option is supported, it returns True and the file name to update.
    """
    # Check the version support
    part    = str(part)[2:-2]
    version = str(version)[2:-2]
    eth_port = []
    uut_part_number = ""
    eth_port = get_enp_interface(conn)

    try:
        update_part_number = (NIC.fw[model][part])
        file_name          = NIC.NIC_FW_FILES[(update_part_number, version)]
    except KeyError, e:
        logging.error("Model: %s does not support version: %s "
                %(model, version))
        exit(1)

    # Check for the part installed in the node
    for i in eth_port:
        uut_part_number = get_sub_system_from_eth(conn, i)
        if update_part_number == uut_part_number:
            logging.debug("Found part %s " %uut_part_number)
            break

    # Check the required update and the on-board part.
    if update_part_number != uut_part_number:
        logging.error("Model %s has different part %s vs %s " %(model,
                update_part_number, uut_part_number))
        exit(1)

    return (True, file_name)

'''-------------------------- Main -----------------------------------------'''
def main():
    model, file, version = "", "", ""
    args = parse_args()

    with open(args.log, 'wb') as log:
        try:
            is_logged_in = False
            conn = Connection(logfile=sys.stdout, static_logpath='~/logs/{0}'.format(this_filename))
            is_logged_in = conn.login(args.ip, args.username, args.password,
                           auto_prompt_reset=False, remove_known_hosts=True,
                           ping_before_connect=False)
            eth_port = []
            eth_port = get_enp_interface(conn)
            logging.debug(eth_port)

            # Check if the option to force update is selected
            if args.model:
                if args.part:
                # Check for SIOM from model
                    if args.version:
		        (ret_status, ret_file) = check_support_process(conn,
                            args.model, args.part, args.version)
                    else:
                        logging.error("Missing option -v <version> required")
                        exit(1)
                    if ret_status:
                        logging.debug("Forcing update with version %s "
                                    %(args.version))
                        do_fw_update(conn, ret_file)
                else:
                    logging.error("Missing option -p <part> required")
                    exit(1)
            else:
                # Default - Check for SIOM on the chassis model
                for i in eth_port:
                    print("\n\n++++++ START UPDATE %s ++++++\n\n" %i)
                    part_number = get_sub_system_from_eth(conn, i)
                    intel = part_number.split(":")
                    if intel[0] != "15d9":
                        print("Non Intel part %s, skip the update " %part_number)
                        break
                    fw_version  = get_fw_from_eth(conn, i)
                    (ret_status, ret_file) = check_update_process(conn,
                                             part_number, fw_version)
                    if ret_status:
                        logging.debug("Update %s with %s " %(i, fw_version))
                        do_fw_update(conn, ret_file)
                    else:
                        logging.info("Part %s firmware %s does not require update!" %(part_number, fw_version))
                        print("Part %s firmware %s does not require update!" %(part_number, fw_version))

            print("NIC update completed!")

        except TIMEOUT:
            if conn.output:
                print('{0}'.format(conn.output))
            print('*** Timeout occurred for {0}!'.format(ip))
        finally:
            time.sleep(.1)
            if is_logged_in:
                conn.logout()


if __name__ == '__main__':
    main()
