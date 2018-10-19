#!/usr/local/bin/python2.7

'''
Nutanix
Program Name: update_hba_fw.py

This utility checks the hba firmware version on the LSI-3008IT. If the \
firmware is out of date, it will update with the preferred one from the \
"fw_config.py" file. Our products support only a single HBA that is installed \
on each node of multiple nodes or a chasis single node. We set default is \
control number 0.

The utility saves all logs in uut_logs.
The script can run with the folowing options:

Prerequisites:
    - This module is tested on Python 2.7.15 and is compatible with python \
      2.7 or later.

Usage:
    $ ./hba_firmware_update.py -h
    $ python hba_firmware_update.py -h
    usage: hba_firmware_update.py [-h] [-v version] [-j JSON] [-l LOG] \
        [--username USERNAME] [--password PASSWORD] [--ip IP] \
        [-m model] [-p port] [-v version to update]

    HBA Firmware Update

    optional arguments:
      -h, --help            displays the help message and exits
      -j JSON, --json JSON  Specifies the reference json filename
      -l LOG, --log LOG     Specifies the log filename to be saved as
      --username USERNAME   username for remote login
      --password PASSWORD   password for remote login
      --ip IP               IP for remote login into where data is to be \
                            collected
      -m		    Model
      -p                    Port num (0, 1, 2, ...)
      -v                    HBA version to flash

Examples:
    Updates the HBA on the local system without specifying a file:
        $python hba_firmware_update.py
        or
        $./hba_firmwarare_update.py

    Updates the HBA on the local system with a specific HBA firmware version \
        $python hba_firmware_update.py -p 0 -v 14.00.00.00
        or
        $./hba_firmware_update.py -p 0 -v 14.00.00.00

    Updates the HBA firmware on the remote system with the ip=192.168.2.123 \
    input:
        $python hba_firmware_update.py --ip=192.168.2.123
        or
        $./hba_firmware_update.py --ip=192.168.2.123

    Updates the HBA on the remote ip=192.168.2.123 with the specific HBA \
            port number firmware version:
        $python hba_firmware_update.py --ip=192.168.2.123 -p 0 -v 14.00.00.00
        or
        $./hba_firmware_update.py --ip=192.168.2.123 -p 0 -v 14.00.00.00

    Specifies the file name for the log file containing the retrieved \
    information:
        $python hba_firmware_update.py --ip=192.168.2.123 \
        -l=sn123_hba_firmware_update.log
        or
        $./hba_firmware_update.py --log=sn123_hba_firmware_update.log

    Specifies the file name for the JSON file containing the retrieved \
    information:
        $python hba_firmware_update.py --ip=192.168.2.123 -j=node_sn.json
        or
        $./hba_firmware_update.py --json=node_sn.json

'''

import json
import os
import re
import sys
import time
import argparse
import logging

# Test framework import
import import_me_first

from pexpect.exceptions import TIMEOUT
from lib.connection import Connection
from lib.dec import time_elapsed
import fw_config as HBA

logging.basicConfig(filename="debug_hba_fw.log", level=logging.DEBUG)
#logging.basicConfig(level=logging.DEBUG)

this_filename = os.path.basename(__file__).split('.')[0]

def parse_args():
    '''This function creates a parser object and adds the arguments and
        information regarding the argument to the parser object. It then
        returns the parsed arguments.
    '''

    parser = argparse.ArgumentParser(
        description='This parser gets all input options to do the HBA update')

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
        help='model name to update eg: NX-3060-G6', required=False)
    parser.add_argument(
        '-p', '--port', type=str, 
        help='file name to update', required=False, nargs='+')
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
        logging.error('ERROR: ipmitool fru command returns nothing!')
        sys.exit(1)

    if verbose:
        logging.debug(json.dumps(fru, indent=4))
    return fru

''' ----------------------------- BOARD_ID-----------------------------------'''
#@time_elapsed
def get_hba_model(conn, verbose=False):
    ''' This function gets and returns the part number of the HBA
    '''

    # product has multiple HBA in single node.
    hba_model = []
    hba_model_list = []

    # Command should be in the PXE but it is not 
    CMD = "%s/sas3flash -listall" %HBA.CMD_PATH
    conn.sendline(CMD, conn.PROMPT)
    hba_model = re.findall(r'\d\s+\w+\d+[0-9$]', conn.output)
    if hba_model:
        for i in hba_model:
            hba = re.findall(r'\w+\d+[0-9$]', i)
            hba = str(hba)[2:-2]
            hba_model_list.append(hba)

    # Check if the current model flashed with IR
    CMD = "%s/sas3flash -list" %HBA.CMD_PATH
    conn.sendline(CMD, conn.PROMPT)
    if conn.output:
        logging.debug("conn.output %s " %conn.output)
        hba_obj = re.search(r'Board Name\s+[:]\s+\w+[-]\w+', 
                conn.output, re.I|re.M)
        hba = hba_obj.group()
        logging.debug(hba)
        if hba:
            hba_obj = re.search(r'\w+\d+[-]\w+', hba)
            hba_model = hba_obj.group()
            logging.debug(hba_model)
            if hba_model != "LSI3008-IT":
                logging.error("The current fw update won't accept IR firmware")
                exit(1)

    if verbose:
        logging.debug(json.dumps(hba_model_list, indent=4))

    return hba_model_list

''' ----------------------------- HBA_VERSION ------------------------------'''
#@time_elapsed
def get_hba_version(conn, verbose=False):
    '''This function checks for the versions on the node or the chasis.
    '''

    # Get hba version
    hba_version = []
    hba_version_list = []

    # Command should be in the PXE but it is not 
    CMD = "%s/sas3flash -listall" %HBA.CMD_PATH
    conn.sendline(CMD, conn.PROMPT)
    hba_version = re.findall(r'\SAS\d{4}\W\w\d\W\s+\d+\.\d+\.\d+\.\d+', 
            conn.output)
    logging.debug(hba_version)
    if hba_version:
        for i in hba_version:
            version = re.findall(r'\d+\.\d+\.\d+\.\d+', i)
            hba_version_list.append(version)

    if verbose:
        logging.debug(json.dumps(hba_version_list, indent=4))

    return hba_version_list

''' --------------------------- Check HBA FW Acceptable --------------------'''
#@time_elapsed
def is_fw_acceptable(conn, hba_ctrl, hba_version, verbose=False):
    '''This function checks to see if the HBA reading from the controller is
       acceptable. If the firmware is in the list of acceptable firmwares, it 
       returns True.  
    '''

    if (hba_version in HBA.HBA_FW_ACCEPTABLE[hba_ctrl]):
        logging.debug("HBA firmware version: %s is acceptable" %hba_version)

        return True
    else:
        logging.debug("HBA fw version: %s is not acceptable and an update \
                       is required." %hba_version)

        return False

''' --------------------- Check HBA FW Update Conflict --------------------'''
#@time_elapsed
def is_update_conflict(conn, hba_ctrl, hba_version, prefer_hba_version, 
        verbose=False):
    '''This function checks if the HBA version on the board will be in conflict
        if we update to the preferred one. If the update causes a conflict, it 
        returns True
    '''
    if (hba_version in HBA.HBA_FW_CONFLICT[(hba_ctrl, prefer_hba_version)]):
        logging.debug("HBA version update from version: % to version: % " + 
                "will cause a conflict" %(hba_version, prefer_hba_version))
        return True
    else:
        logging.debug("HBA update is not conflicted")
        return False

''' ----------------------------- update_process ---------------------------'''
@time_elapsed
def do_fw_update(conn, ctrl_num, file_name):
    '''The HBA update flashes 3 different files:
        Step1: sas3flash -c ctrl_num -f 3008IT.ROM
        Step2: sas3flash -c ctrl_num -b mptsas3.rom
        Step3: sas3flash -c ctrl_num -b mpt3x64.rom 
    '''
    logging.debug("update ctrl %s file %s " %(ctrl_num, file_name))

    # Update the HBA file 3008IT.ROM
    CMD="%s/sas3flash -c "%HBA.CMD_PATH+str(ctrl_num) +' -f '
    conn.sendline(CMD +file_name, "Successfully", timeout=60)

    # Clear the buffer
    conn.sendline(' ', conn.PROMPT)
    logging.debug("HBA flashed %s  %  successful !!!. " %(ctrl_num, file_name))

    # Update the HBA BIOS mptsas3.rom
    CMD="%s/sas3flash -c "%HBA.CMD_PATH+str(ctrl_num) +' -b '
    path = re.search(r'(.+)[.][0]+\/', file_name)
    file_name = path.group()+'mptsas3.rom'
    conn.sendline(CMD +file_name, "Successfully", timeout=40)

    # Clear the buffer
    conn.sendline(' ', conn.PROMPT)
    logging.debug("HBA flashed %s  %  successful !!!. " %(ctrl_num, file_name))

    # Update the HBA file mpt3x64.rom
    file_name = path.group()+'mpt3x64.rom'
    conn.sendline(CMD +file_name, "Successfully", timeout=30)

    # Clear the buffer
    conn.sendline(' ', conn.PROMPT)
    logging.debug("HBA flashed %s  %  successful !!!. " %(ctrl_num, file_name))


''' --------------------------- HBA Update Process -------------------------'''
@time_elapsed
def check_update_process(conn, ctrl_num, part_number, fw_version):
    '''This function checks the current firmware to see if it requires
       an update and if it is updatable. If the current firmware is updatable,
       return True. The function also returns the file name to update.
    '''

    try:
        prefer_hba_version = HBA.HBA_FW_PREFER[part_number]
        logging.debug("prefer version %s" %prefer_hba_version)
        file_name = HBA.HBA_FW_FILES[(part_number, prefer_hba_version)]
    except KeyError, e:
        logging.error("The version %s is not supported" %prefer_hba_version)
        exit(1)

    #First check for the same preferred firmware
    if fw_version == prefer_hba_version:
        logging.debug("Version match")
        logging.info("Current HBA version "+fw_version+" is matched ")
        # TESTING - Commend out the return to force update
        #return (False, file_name) 
    else:
        logging.debug("Version mismatch. Next, checking version in the \
                       acceptable list")

    # Second check if the HBA is acceptable
    if is_fw_acceptable(conn, part_number, fw_version):
        logging.debug("Version is acceptable")
        logging.info("Current HBA version "+fw_version+" is acceptable")
        # TESTING - Commend out the return to force update
        #return (False, file_name)
    else:
        logging.debug("Version is not acceptable. An update is required")
        logging.info("Current HBA version "+fw_version+" is outdated \
                      unqualified. Running HBA update process:")

    # Third check if the update is conflicted
    if is_update_conflict(conn, part_number, fw_version, prefer_hba_version):
        logging.error("Update is conflicted. Exiting.")
        exit(1)
    else:
        logging.debug("Update is not conflicted. Proceed with update...")

    return(True, file_name)

'''-------------------------------------------------------------------------'''
def check_support_process(conn, model, version):
    '''This function checks if the forced update option is available. If the
        options are supported, it returns True and the file name to update.
    '''
    # Check the version support
    version = str(version)[2:-2]

    try:
        update_part_number = (HBA.fw[model]["HBA"])
        uut_part_number    = get_hba_model(conn)
        uut_part_number    = str(uut_part_number)[2:-2]
        file_name          = HBA.HBA_FW_FILES[(update_part_number, version)]
    except KeyError, e:
        logging.error("Model %s is not supported " %model)
        exit(1)

    # Check the required update and the on-board part.
    if update_part_number != uut_part_number:
        logging.error("Model %s has different part %s vs %s " %(model,
            update_part_number, uut_part_number))
        exit(1)

    return (True, file_name)



''' -------------------------------- Main -----------------------------------'''
def main():
    model, version = "", ""
    args = parse_args()

    with open(args.log, 'wb') as log:
        try:
            is_logged_in = False
            conn = Connection(logfile=sys.stdout, 
                    static_logpath='~/logs/{0}'.format(this_filename))
            is_logged_in = conn.login(args.ip, args.username, args.password,\
                                      args.model, auto_prompt_reset=False,  \
                                      remove_known_hosts=True, ping_before_connect=False)

            # Check if the option to force update is selected
            if args.model:
                logging.debug(args.model)
                if (args.version):
                    (ret_status, ret_file) = check_support_process(conn, 
                            args.model, args.version)
                    if ret_status:
                        logging.debug("Forcing update with file_name %s version \
                                       %s " %(args.file, args.version))
                        do_fw_update(conn, 0, ret_file)
                else:
                    logging.error("Missing option -v <version> required")
                    exit(1)

            else:
                # Update by default
                hba_number = []
                hba_firmware = []
                hba_numbers  = get_hba_model(conn)
                hba_firmware = get_hba_version(conn)

                print(hba_numbers, hba_firmware)
                for i in range(len(hba_numbers)):
                    part_number = hba_numbers[i]
                    fw_version  = hba_firmware[i]
                    fw_version  = str(fw_version)[2:-2]
                    (ret_status, ret_file) = check_update_process(conn, i, 
                            part_number, fw_version)
                    if ret_status:
                        do_fw_update(conn, i, ret_file)
                    else:
                         logging.debug("Current firmware port %s does not \
                                        require an update!" %i)
       
            print("HBA Update successful!")
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
