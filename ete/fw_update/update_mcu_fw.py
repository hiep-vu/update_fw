#!/usr/local/bin/python2.7

'''
Nutanix
Program Name: update_mcu_fw.py

This utility checks the MCU firmware version on the model. If the \
firmware is out of date, it will update with the preferred one from the \
"fw_config.py". 

The utility saves all of its logs in uut_logs.
The script also has the options to force the following updates:

Prerequisites:
    - This module is tested on Python 2.7.15 and is compatible with python
      2.7 or later.

Usage:
    $ ./update_mcu_fw.py -h
    $ python update_mcu_fw.py -h
    usage: update_mcu_fw.py [-h] [-l LOG] \
	[--username USERNAME] [--password PASSWORD] [--ip IP] [-m model] \
        [-v version]

    MCU Firmware Update

    optional arguments:
      -h, --help            displays the help message and exits
      -j JSON, --json JSON  Specifies the reference json filename
      -l LOG, --log LOG     Specifies the log filename to be saved as
      --username USERNAME   username for remote login
      --password PASSWORD   password for remote login
      --ip IP               IP for remote login where data is to be collected
      -m                    Model
      -v                    MCU path/file to flash

Examples:
    Updates the MCU on the local system without specifying a file:
        $python update_mcu_fw.py
        or
	$./update_mcu_fw.py

    Updates the MCU on the local system with the mother board "NX-8036-G6"
    and the specific version:
        $python update_mcu_fw.py -m NX-8036-G6 -v 4.0
        or
	$./update_mcu_fw.py -m NX-8036-G6 -v 4.0

    Updates the MCU firmware on the remote system with the ip=192.168.2.123 
    input:
        $python update_mcu_fw.py --ip=192.168.2.123
        or
	$./update_mcu_fw.py --ip=192.168.2.123

    Updates the MCU on the remote ip=192.168.2.123 with the mother board \
    "NX-8036-G6" and the specific version:
        $python update_mcu_fw.py --ip=192.168.2.123 -m NX-8036-G6 -v 4.0 
        or
	$./update_mcu_fw.py --ip=192.168.2.123 -m NX-8036-G6 -v 4.0

    Specifies the file name for the log file containing the retrieved \
    information:
        $python update_mcu_fw.py --ip=192.168.2.123 -l=sn123_update_mcu_fw.log
        or
        $./update_mcu_fw.py --log=sn123_update_mcu_fw.log

    Specifies the file name for the JSON file containing the retrieved \
    information:
        $python update_mcu_fw.py --ip=192.168.2.123 -j=node_sn.json
	or
        $./update_mcu_fw.py --json=node_sn.json

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
import fw_config as MCU

logging.basicConfig(filename="debug_mcu_fw.log", level=logging.DEBUG)
#logging.basicConfig(level=logging.DEBUG)

this_filename = os.path.basename(__file__).split('.')[0]

def parse_args():
    '''This function creates a parser object and adds the arguments and
       information regarding the argument to the parser object. It then
       returns the parsed arguments.
    '''
    parser = argparse.ArgumentParser(
        description='This parser gets all input options to do the MCU update')
    
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
        '-v', '--version', type=str,
        help='firmware version to update', required=False, nargs='+')

    args = parser.parse_args()

    return args

''' ----------------------------- GET FRU INFO ------------------------------'''
def get_fru_info(conn, verbose=False):
    fru = {}
    '''This function gets and returns the model from the chasis
    '''

    # Get FRU info if it does not exist
    conn.sendline('ipmitool fru', conn.PROMPT)
    if conn.output:
        for line in conn.output.split('\n')[1:]:
            if ' : ' in line:
                k, v = line.split(' : ', 1)
                fru[k.strip()] = v.strip()
    else:
        logging.debug('ERROR: ipmitool fru command returns nothing!')
        sys.exit(-1)

    if verbose:
        logging.debug(json.dumps(fru, indent=4))
    return fru

''' ----------------------------- MCU INFO ----------------------------------'''
#@time_elapsed
def get_part_info(conn, verbose=False):
    '''This function gets and returns the part number of the MCU
    '''

    conn.sendline('/usr/bin/ipmicfg-linux.x86_64 -tp info', conn.PROMPT)
    if conn.output:
        mcu_info = re.search(r'[B][P][N]\S+', conn.output, re.I|re.M)
        mcu_info = mcu_info.group()

    if verbose:
        logging.debug(json.dumps(mcu_info, indent=4))

    return mcu_info

''' ----------------------------- MCU_VERSION ------------------------------'''
#@time_elapsed
def get_part_version(conn, verbose=False):
    '''This function checks for the versions on the node or the chasis.
    '''

    # Get mcu version
    conn.sendline('/usr/bin/ipmicfg-linux.x86_64 -tp info', conn.PROMPT)
    if conn.output:
        logging.debug(conn.output)
        mcu_version = re.search(r'[M][C][U]\s+(.+)', conn.output)
        logging.debug(mcu_version.group())
        mcu_version = mcu_version.group()
        if mcu_version:
            mcu_obj = re.search(r'\d+[.]\d+', mcu_version)
            logging.debug(mcu_obj.group())
            mcu_version = mcu_obj.group()
            logging.debug("MCU version: %s" %mcu_version)

    if verbose:
        logging.debug(json.dumps(mcu_version, indent=4))

    return mcu_version

''' --------------------------- Check MCU FW Acceptable --------------------'''
#@time_elapsed
def is_fw_acceptable(conn, mcu_info, mcu_version, verbose=False):
    '''This function checks to see if the MCU reading from the controller is
       acceptable. If the firmware is in the list of acceptable firmwares, it
       returns True.
    '''

    if (mcu_version in MCU.MCU_FW_ACCEPTABLE[mcu_info]):
        logging.debug("mcu firmware Version: %s is acceptable" %mcu_version)
        # TESTING
        #return True
    else:
        logging.debug("mcu firmwere Version: %s is not acceptable and an update\
                       is required." %mcu_version)
        return False

''' --------------------- Check MCU FW Update Conflict --------------------'''
#@time_elapsed
def is_update_conflict(conn, mcu_info, mcu_version, prefer_mcu_version, 
        verbose=False):
    '''This function checks if the MCU version on the board will be in conflict
       if we update to the preferred one. If the update causes a conflict, it 
       returns True.
    '''
    if (mcu_version in MCU.MCU_FW_CONFLICT[(mcu_info, prefer_mcu_version)]):
        logging.error("FAIL:MCU:UPDATE:Detected="+str(mcu_version)+":Couldn't\
                update to the preferred version")
        logging.debug("MCU version update from Version: % to Version: % " + 
                "will be conflicted" %(mcu_version, prefer_mcu_version))
        return True
    else:
        logging.debug("MCU update is not conflicted")
        return False

""" ----------------------------- do_fw_update --------------------------------------"""
#@time_elapsed
def do_fw_update(conn, file_name):
    '''Get the MCU file name and performs the update.
    '''
    # Check if the update files exists.
    conn.sendline('ls '+file_name, conn.PROMPT, timeout=10)
    conn.output = conn.output.split()

    if "cannot access" in conn.output:
        logging.debug ("File not found ")
        logging.error(conn.output)
        sys.exit(1)
    else:
        logging.debug("Found file. Performing firmware update.")

    logging.debug("Update file location is %s " %(file_name))

    # Changes to directory where the tool requires files to support update.
    conn.sendline('cd /bin/', conn.PROMPT, timeout=20)
    CMD = "/bin/ipmicfg -tp mcuupdate %s" %file_name
    logging.debug("Warning, the update will reset the power and all nodes will reboot")
    logging.debug("Please do not turn off the power!")
    conn.sendline(CMD, "....", timeout=100)
    conn.sendline(' ', "....", timeout=20)

''' --------------------------- MCU Update Process for default -------------------------'''
#@time_elapsed
def check_update_process(conn, part_number, fw_version): 
    '''This function checks the current firmware to see if it requires
       an update and if it is updatable. If the current firmware is updatable,
       return True. The function also returns the file name to update.
    '''

    prefer_mcu_version = MCU.MCU_FW_PREFER[part_number]
    logging.debug("expect_ver %s" %(prefer_mcu_version))

    file_name = MCU.MCU_FW_FILES[(part_number, prefer_mcu_version)]
    logging.debug(file_name)

    # First check for the same preferred firmware
    if fw_version == prefer_mcu_version:
        logging.info("Current MCU.MCU version "+fw_version+" is matched ")
        #TESTING - Comment out return to force update default
        return (False, file_name)
    else:
        logging.debug("Version mismatch. Next, checking version in the acceptable list")


    # Second check if the MCU.MCU is acceptable
    if is_fw_acceptable(conn, part_number, fw_version):
        logging.info("Current MCU.MCU version "+fw_version+" is acceptable")
        #TESTING - Comment out return to force update default
        return(False, file_name) 
    else:
        logging.debug("Current firmware is not acceptable. An update is required")

    # Third check if the update is conflicted with the current one
    logging.debug("Update %s %s %s " %(part_number, fw_version, prefer_mcu_version))
    if is_update_conflict(conn, part_number, fw_version, prefer_mcu_version):
        logging.error("Update is conflicted. Exiting.")
        exit(1)
    else:
        logging.debug("Update is not conflicted. Proceed with update...")

    return (True, file_name)

'''---------------------- Check input args ---------------------------------'''
def check_support_process(conn, model, version):
    '''The function checks if the forced update option is available. If the 
        options are supported, it returns True and the file name to update.
    '''
    # Check the version support
    version = str(version)[2:-2]

    try:
        uut_part_number    = get_part_info(conn)
        update_part_number = (MCU.fw[model]["MCU"])
        file_name          = MCU.MCU_FW_FILES[(update_part_number, version)]
    except KeyError, e:
        logging.error("The version %s is not supported" %version)
        exit(1)

    # Check the required update part and the on-board part.
    if update_part_number != uut_part_number:
        logging.error("Model %s has different part %s vs %s " %(model, update_part_number, uut_part_number))
        exit(1)

    return (True, file_name)

'''-------------------------------------------------------------------------'''
def main():
    '''The MCU after updated, will reset the power so the other nodes will 
        be rebooted.
    '''

    model, version =  "", ""
    args = parse_args()
    
    with open(args.log, 'wb') as log:
        try:
            is_logged_in = False
            conn = Connection(logfile=sys.stdout, 
                              static_logpath='~/logs/{0}'.format(this_filename))
            is_logged_in = conn.login(args.ip, args.username, args.password, \
                                      auto_prompt_reset=False, remove_known_hosts=True, 
                                      ping_before_connect=False)

            if args.model:
                # Update by force with model and version
                if args.version:
                   (ret_status, ret_file) = check_support_process(conn, args.model, 
                           args.version)
                   if ret_status:
                       do_fw_update(conn, ret_file)
                else:
                   logging.error("The option -v <version> required")
                   exit(1)
            else:
                # Update by default
                part_number = get_part_info(conn)
                fw_version  = get_part_version(conn)
                (ret_status, ret_file) = check_update_process(conn, part_number, fw_version) 
                if ret_status:
                    do_fw_update(conn, ret_file)
                else:
                    logging.debug("Current firmware does not require an update!")

            print("MCU Update Successful!")
            exit(0)

        except TIMEOUT:
            if conn.output:
                print('{0}'.format(conn.output))
            print('*** Timeout occurred for {0}!'.format(args.ip))
        finally:
            time.sleep(.1)
            if is_logged_in:
                conn.logout()

if __name__ == '__main__':
    main()
