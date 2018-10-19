#!/usr/local/bin/python2.7

'''
Program Name: update_bios_fw.py

This utility checks and update the BIOS firmware version on the mother board. \
If the firmware is outdated, it will update the firmware with the preferred \
one from the "fw_config.py". The options -m <model> and the option -v \
<version> are required to force the update. This utility saves all logs into \
uut_logs.

Prerequisites:
    - This module is tested on Python 2.7.15 and is compatible with python
      2.7 or later.

Usage:
    $ ./update_bios_fw.py -h
    $ python update_bios_fw.py -h
    usage: update_bios_fw.py [-h] [-f path/firmware] [-j JSON] [-l LOG] \
            [--username USERNAME] [--password PASSWORD] [--ip IP] [-m Model] \
            [-v bios version]

    BIOS Firmware Update

    optional arguments:
      -h, --help            show this help message and exit
      -j JSON, --json JSON  Specify the reference json filename
      -l LOG, --log LOG     Specify the log filename to be saved as
      --username USERNAME   username
      --password PASSWORD   password
      --ip IP               Destination IP to collect information on
      - m  		    Model
      - v                   Bios version to force update

Examples:
    Updates the BIOS in-band by default:
        python update_bios_fw.py
        or
        ./update_bios_fw.py

    Updates the BIOS in-band with the specific model and BIOS version
        python update_bios_fw.py -m NX-3060-G6 -v PB20.001 
        or
        ./update_bios_fw.py -m NX-1065-G6 -v PU11.144

    Updates the BIOS firmware by default on the remote with the ip: 192.168.2.123
        python update_bios_fw.py --ip=192.168.2.123
        or
        ./update_bios_fw.py --ip=192.168.2.123

    Updates the BIOS firmware on the remote ip: 192.168.2.123 with model, BIOS version
        python update_bios_fw.py --ip=192.168.2.123 -m NX-3060-G6 -v PU11.144
        or
        ./update_bios_fw.py --ip=192.168.2.123 -m NX-1065-G6 -v PU11.144

    Specifies the file name for the log file containing the retrieved \
    information:
        python update_bios_fw.py --ip=192.168.2.123 -l=sn123_update_bios_fw.log
        or
        ./update_bios_fw.py --log=sn123_update_bios_fw.log

    Specifies the file name for the JSON file containing the retrieved \
    information:
        python update_bios_fw.py --ip=192.168.2.123 -j=node_sn.json
        or
        ./update_bios_fwupdate.py --json=node_sn.json

'''

import json
import os
import re
import sys
import time
import argparse
import logging

# Include the project package into the system path to allow import
package_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, package_path)

# Import your package (if any) below
import import_me_first

from pexpect.exceptions import TIMEOUT
from lib.connection import Connection
from lib.dec import time_elapsed
import fw_config as BIOS

logging.basicConfig(filename="debug_bios_fw.log", level=logging.DEBUG)
#logging.basicConfig(level=logging.DEBUG)

this_filename = os.path.basename(__file__).split('.')[0]

def parse_args():
    ''' This function creates a parser object and adds the arguments and
        information regrading the argument to the parser object. It then
        returns the parsed arguments
    '''
    parser = argparse.ArgumentParser(
        description='This parser gets all input options to do the BIOS update')
    # Add arguments
    parser.add_argument(
        '-l', '--log',
        help='Specify the log filename to be saved as', default='{0}.log'.format(os.path.basename(__file__).split('.')[0]))
    parser.add_argument(
        '--username', required=False,
        help='username', default='root')  # Default username for the PXE server
    parser.add_argument(
        '--password', required=False,
        help='password', default='nutanix/4u')  # Default password for the PXE server
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

''' ----------------------------- BOARD_ID-----------------------------------'''
#@time_elapsed
def get_part_info(conn, verbose=False):
    ''' This function gets and returns the part number of the BIOS
    '''

    conn.sendline('dmidecode -t baseboard', conn.PROMPT)
    if conn.output:
        baseboard_obj = re.search(r'[P][r][o][d]\w+\s+[N]\w+[:]\s+[a-zA-z0-9]+[.-]\w+', conn.output, re.I|re.M)
        bios_baseboard = baseboard_obj.group()
        if bios_baseboard:
            baseboard_obj = re.search(r'[a-zA-Z0-9]+[.-]\w+', bios_baseboard)
            bios_baseboard = baseboard_obj.group()

    if verbose:
        logging.debug(json.dumps(bios_baseboard, indent=4))

    return bios_baseboard

''' ----------------------------- BIOS_VERSION ------------------------------'''
#@time_elapsed
def get_part_version(conn, verbose=False):
    ''' This function gets and returns the BIOS's version
    '''
    conn.sendline('dmidecode -t bios', conn.PROMPT)
    if conn.output:
        bios_obj = re.search(r'[V][e][r]\w+\:\s+\w+\S+', conn.output, re.I|re.M)
        bios_version = bios_obj.group()
        if bios_version:
            bios_obj = re.search(r'\w+\d+\S+', bios_version)
            bios_version = bios_obj.group()

    if verbose:
        logging.debug(json.dumps(bios_version, indent=4))

    return bios_version

''' --------------------------- Check BIOS FW Acceptable --------------------'''
#@time_elapsed
def is_fw_acceptable(conn, bios_baseboard, bios_version, verbose=False):
    ''' This function checks if the BIOS firmware reading from the baseboard is
        acceptable. If the firmware is in the list of acceptable firmwares, it
        returns True
    '''

    if (bios_version in BIOS.BIOS_FW_ACCEPTABLE[bios_baseboard]):
        logging.debug("bios firmware Version: %s is acceptable" %bios_version)
        return True
    else:
        logging.debug("BIOS firmware Version: %s is not acceptable and requires \
                an update." %bios_version)
        return False

''' --------------------- Check BIOS FW Update Conflict --------------------'''
#@time_elapsed
def is_update_conflict(conn, bios_baseboard, bios_version, prefer_bios_version,
        verbose=False):
    ''' This function checks if the BIOS version will be in conflict when we
        update to the preferred one. If the update causes a conflict, return
        True
    '''
    if (bios_version in BIOS.BIOS_FW_CONFLICT[(bios_baseboard, prefer_bios_version)]):
        logging.error("FAIL:BIOS:UPDATE:Detected="+str(bios_version)+":Couldn't update to the prefer version")
        logging.debug("bios version updated from version: % to cersion: % will be conflicted" %(bios_version, prefer_bios_version))
        return True
    else:
        logging.debug("bios update is not conflicted")
        return False

''' ------------------------------ check_update_msg -------------------------'''
#@time_elapsed
def is_reboot_action(conn, bios_update_msg, verbose=False):
    """ Some G4G5 BIOS versions have different FDT from the updated one. After
        the 1st update, the UUT requires a soft reboot and a re-run of the
        updates for FDT.
    """
    msg = bios_update_msg
    reboot_action = re.search(r'Manual steps are required',msg)
    if reboot_action:
        logging.debug("Soft reboot required before the FDT update")
        logging.debug("wait 320 seconds to reboot")
        conn.sendline('reboot -f', "Rebooting.")
        time.sleep(320)
        return True
    else:
        logging.debug("UUT update completed !")
        logging.debug("UUT update completed !")
        return False

""" ----------------------------- do_fw_update ------------------------------"""
#@time_elapsed
def do_fw_update(conn, file_name):
    """ This function gets the BIOS file name and does the update.
    """
    logging.debug("Update file location %s " %(file_name))
    logging.debug("Warning, the update process takes 7 minutes to complete. " + \
            "Please don't turn off the power!!!")
    logging.debug("...")

    # Check if the update files exists.
    conn.sendline('ls '+file_name, conn.PROMPT, timeout=10)

    if "cannot access" in conn.output:
        logging.error ("File not found ")
        logging.debug(conn.output)
        sys.exit(1)
    else:
        logging.debug("Found file. Performing firmware update.")

    # WARNING:Must power cycle or restart the system
    #CMD = "%s/sumtool -c UpdateBios --file " %BIOS.CMD_PATH
    CMD = "/usr/bin/sumtool -c UpdateBios --file "
    conn.sendline(CMD +file_name, "WARNING", timeout=800)
    """
    # Applied for remote
    if is_reboot_action(conn, conn.output):
        return True
    else:
        # Clear the buffer
        conn.sendline(' ', conn.PROMPT)
        # Load Bios config after the flash completed
        logging.debug("Load BIOS config after update.")
        CMD = "%s/sumtool -c LoadDefaultBiosCfg " %BIOS.CMD_PATH
        conn.sendline(CMD, "configuration is loaded", timeout=30)
        conn.sendline(' ', conn.PROMPT)
        logging.debug("BIOS flash is successful !!!. The node is required " +
                "to be re-booted for the firmware update to take effect.")
        return False
    """
    return False

''' --------------------------- check_update_process ------------------------'''
#@time_elapsed
def check_update_process(conn, part_number, fw_version):
    """
    Args inputs:
        part_number - The BIOS mother board part
        fw_version  - The current BIOS firmware
    Funtion:
        This function checks if the current firmware requires an update, and if
        it is updatable. If the current firmware is updatable, return True. The
        function also returns the file name to update.
    """

    try:
        # Check the preferred version from the list
        prefer_bios_version = BIOS.BIOS_FW_PREFER[part_number]
        logging.debug("expect_ver %s" %(prefer_bios_version))
        file_name           = BIOS.BIOS_FW_FILES[(part_number, prefer_bios_version)]
        logging.debug(file_name)
    except KeyError, e:
        logging.error("The version %s is not supported" %part_number)
        exit(1)

    # First check for the update requirement
    if fw_version == prefer_bios_version:
        logging.debug("Current BIOS firmware versions matches with preferred " +
                "BIOS firmware. Update not required")
        logging.info("Current BIOS firmware version: " + fw_version+" is matched ")
        # TESTING - Comment out return value to ignore prefer bios check
        return (False, file_name)
    else:
        logging.debug("Current BIOS version mis-matches with preferred BIOS " +
                "firmware version. Checking in the acceptable firmware list")

    # Second check if the BIOS is acceptable
    if is_fw_acceptable(conn, part_number, fw_version):
        logging.debug("The current BIOS firmware version is acceptible and " +
                "no firmware updates are required")
        logging.info("Current BIOS version: " + fw_version + " is acceptable")
        # TESTING - Comment out return value to ignore acceptable bios check
        return (False, file_name)
    else:
        logging.debug("The current BIOS requires the update")
        logging.info("Current BIOS version " + fw_version + " is outdated/ " +
                "un-qualified. An update is required")

    # Third check if the update is conflict
    if is_update_conflict(conn, part_number, fw_version, prefer_bios_version):
        logging.error("The update version conflicts with the current " +
                "version. Exiting.")
        exit(1)
    else:
        logging.debug("The update version is not conflicted with the current " +
                "version")

    return (True, file_name)

'''------------------------ check_support_process ---------------------------'''

def check_support_process(conn, model, version):
    """ This function checks if the forced update option is available. If the
        option is supported, it returns True and the file name to update.
    """
    # Check the version support
    version = str(version)[2:-2]

    try:
        update_part_number = (BIOS.fw[model]["BIOS"])
        uut_part_number    = get_part_info(conn)
        file_name          = BIOS.BIOS_FW_FILES[(update_part_number, version)]
    except KeyError, e:
        logging.error("The version %s is not supported" %version)
        exit(1)

    # Check the required update and the on-board part.
    if update_part_number != uut_part_number:
        logging.error("Model %s has different part %s vs %s " %(model, update_part_number, uut_part_number))
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
            is_logged_in = conn.login(args.ip, args.username, args.password,
                    args.model, auto_prompt_reset=False,
                    remove_known_hosts=True, ping_before_connect=False)

            if args.model:
                # Update with options -m and -v
                if (args.version):
                    (ret_status, ret_file) = \
                        check_support_process(conn, args.model, args.version)
                    if ret_status:
                        logging.debug("Forcing update with verson %s " %(args.version))
                        if do_fw_update(conn, ret_file):
                            # Redo the update after boot up
                            is_logged_in = False
                            conn = Connection(logfile=sys.stdout,
                                    static_logpath='~/logs/{0}'.format(this_filename))
                            is_logged_in = conn.login(args.ip, args.username,
                                        args.password, args.model,
                                        auto_prompt_reset=False,
                                        remove_known_hosts=True,
                                        ping_before_connect=True)
                            print("Files will be updated after reboot")
                            time.sleep(500)
                            if do_fw_update(conn, ret_file):
                                logging.error("Update process is bad")
                                exit(1)
                            else:
                                print("Update completed!")
                        else:
                            # Update finished
                            print("Update completed!")
                else:
                    logging.error("Missing option -v <version>")
                    exit(1)

            else:
                # Default update: The script checks the component part number, current firmware
                part_number  = get_part_info(conn)
                fw_version   = get_part_version(conn)
                (ret_status, ret_file) =  check_update_process(conn,
                        part_number, fw_version)
                if ret_status:
                    if do_fw_update(conn, ret_file):
                        is_logged_in = False
                        conn = Connection(logfile=sys.stdout,
                                static_logpath='~/logs/{0}'.format(this_filename))
                        is_logged_in = conn.login(args.ip, args.username,
                                args.password, args.model,
                                auto_prompt_reset=False,
                                remove_known_hosts=True,
                                ping_before_connect=True)
                        print("update files after reboot")
                        time.sleep(500)
                        if update_process(conn, ret_file):
                            logging.error("Update process is bad")
                            exit(1)
                        else:
                            print("Update completed!")
                    else:
                        # Update finished
                        logging.debug("Update completed!")
                else:
                    logging.debug("BIOS does not require an update")
                    exit(0)

            print("BIOS update successful!")
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
