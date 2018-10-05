#!/usr/local/bin/python2.7

"""
Program Name: update_bmc_fw.py

This utility checks and updates the BMC firmware version on the model. If the \
firmware is outdated, it will update the firmware with the preferred one from \
"fw_config.py". This script also has the option to force-update a specific \
firmware version. Log files and json files will be saved into the pre-existing \
directory: uut_logs.

Prerequisites:
    - This module is tested on Python 2.7.15 and is compatible with python \
      2.7 or later.

Usage:
    $ ./bmc_firmware_update.py -h
    $ python bmc_firmware_update.py -h
    usage: bmc_firmware_update.py [-h] [-m motherboard model] [-v version] \
            [-l LOG] [-j JSON] [--username USERNAME] \
            [--password PASSWORD] [--ip IP]

    optional arguments:
      -h, --help            displays the help message, then exit
      -m                    the motherboard model
      -v                    the firmware version you want to install
      -l, --log             name for the log file to be saved as, or else it \
                            would be the default name
      -j                    name for the json file to be saved as, or else it \
                            would be the default name
      --username            username for remote login
      --password            password for remote login
      --ip                  IP for remote login into where data is to be \
                            collected

Examples:
    Updates the BMC on the local system without specifying a file path:
        $python update_bmc_fw.py
        or
        $./update_bmc_fw.py

    Updates the BMC on the local system with the motherboard "NX-8036-G6" and \
    specific BMC firmware version "4.0":
        $python update_bmc_fw.py -m NX-8036-G6  -v 4.0
        or
        $./update_bmc_fw.py -m NX-8036-G6  -v 4.0

    Updates the BMC firmware on a remote system with the ip: 192.168.2.123:
        $python update_bmc_fw.py --ip=192.168.2.123
        or
        $./update_bmc_fw.py --ip=192.168.2.123

    Updates the BMC on the remote ip: 192.168.2.123 with the motherboard: \
    "NX-8036-G6" and specific BMC firmware version "4.0":
        $python update_bmc_fw.py --ip=192.168.2.123 -m NX-8036-G6 -v 4.0
        or
        $./update_bmc_fw.py --ip=192.168.2.123 -m NX-8036-G6 -v 4.0

    Specifies the file name for the log file containing the retrieved \
    information:
        $python update_bmc_fw.py --ip=192.168.2.123 -l=sn123_update_bmc_fw.log
        or
        $./update_bmc_fw.py --log=sn123_update_bmc_fw.log

    Specifies the file name for the JSON file containing the retrieved \
    information:
        $python update_bmc_fw.py --ip=192.168.2.123 -j=node_sn.json
        or
        $./update_bmc_fw.py --json=node_sn.json

"""
import argparse
import json
import os
import re
import sys
import time
import logging

# Import your package (if any) below
import import_me_first

from pexpect.exceptions import TIMEOUT
from lib.connection import Connection
from lib.dec import time_elapsed
import fw_config as BMC

logging.basicConfig(filename="debug_bmc_fw.log", level=logging.DEBUG)
#logging.basicConfig(level=logging.DEBUG)

this_filename = os.path.basename(__file__).split('.')[0]

def parse_args():
    ''' This function creates a parser object and adds the arguments and
        information regarding the argument to the parser object. It then
        returns the parsed arguments
    '''
    parser = argparse.ArgumentParser(
        description='This parser gets all input options to do the BMC update')

    # Add arguments
    parser.add_argument(
        '-l', '--log', help='Specify the log filename to be saved as',
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

''' ----------------------------- BOARD_ID ----------------------------------'''
#@time_elapsed
def get_part_info(conn, verbose=False):
    ''' This function gets and returns the part number of the mother board's
        board management controller
    '''

    conn.sendline('dmidecode -t baseboard', conn.PROMPT)
    if conn.output:
        baseboard = re.search(r'[P][r][o]\S+\s+\S+\s+\S+', conn.output,
                re.I|re.M)
        bmc_baseboard = baseboard.group()
        if bmc_baseboard:
            baseboard_obj = re.search(r'\w+\d+\w+[-]\w+', bmc_baseboard)
            bmc_baseboard = baseboard_obj.group()
    if verbose:
        logging.debug(json.dumps(bmc_baseboard, indent=4))
    return bmc_baseboard

''' ----------------------------- BMC_VERSION -------------------------------'''
#@time_elapsed
def get_part_version(conn, verbose=False):
    ''' This function gets and returns the board management controller's
        version
    '''
    conn.sendline('/usr/bin/ipmicfg-linux.x86_64 -ver', conn.PROMPT)
    if conn.output:
        logging.debug(conn.output)
        bmc_obj = re.search(r'[V][e][r]\w+[:]\s+(.+)\d+', conn.output,
                re.I|re.M)
        logging.debug(bmc_obj.group())
        bmc_version = bmc_obj.group()
        if bmc_version:
            bmc_obj = re.search(r'\d+[-.](.+)\d+', bmc_version)
            logging.debug(bmc_obj.group())
            bmc_version = bmc_obj.group()
            logging.debug("BMC version: %s" %bmc_version)
    if verbose:
        logging.debug(json.dumps(bmc_version, indent=4))
    return bmc_version

''' --------------------------- Check BMC FW Acceptable ---------------------'''
#@time_elapsed
def is_fw_acceptable(conn, bmc_baseboard, bmc_version, verbose=False):
    ''' This function checks if the firmware reading from the BMC is acceptable.
        If the firmware is in the list of acceptable firmwares, it returns True.
    '''

    if (bmc_version in BMC.BMC_FW_ACCEPTABLE[bmc_baseboard]):
        logging.debug("BMC firmware version: %s is acceptable" %bmc_version)
        # TESTING - Commend out return to ignore the firmware acceptable check
        return True
    else:
        logging.debug("BMC firmware version: %s is not acceptable and an update is required." %bmc_version)
        return False

''' --------------------- Check BMC FW Update Conflict ----------------------'''
#@time_elapsed
def is_update_conflict(conn, bmc_baseboard, bmc_version, prefer_bmc_version,
        verbose=False):
    ''' This function checks if the BMC version on the board will be in conflict
        when we update to the preferred one. If the update causes a conflict,
        return True
    '''
    if (bmc_version in BMC.BMC_FW_CONFLICT[(bmc_baseboard,
            prefer_bmc_version)]):
        logging.error("FAIL:BMC:UPDATE:Detected=" + str(bmc_version) +
                ":Couldn't update to the preferred version")
        logging.debug("BMC version updated from Version: % to Version: % " +
                "will cause a conflict" %(bmc_version, prefer_bmc_version))
        return True
    else:
        logging.debug("BMC update is not conflicted")
        return False

''' ---------------------- BMC set to factory default -----------------------'''
#@time_elapsed
def bmc_set_to_default(conn):
    """This function sets the BMC to factory default
    """
    # Set BMC to factory default
    conn.sendline('/usr/bin/ipmicfg-linux.x86_64 -fdl', "completed", timeout=10)
    logging.debug("Console ouput %s " %conn.output)

''' -------------------------- BMC Cold Reboot ------------------------------'''
#@time_elapsed
def bmc_set_cold_reboot(conn):
    """
    This function sets the BMC to cold reboot
    """
    # Cold reboot BMC
    conn.sendline('/usr/bin/ipmitool bmc reset cold', "#", timeout=10)
    logging.debug("Console ouput %s " %conn.output)
    logging.debug("Wait 2 minutes for the system boot up")

    time.sleep(120)

''' ------------------------ do_fw_update -----------------------------------'''
#@time_elapsed
def do_fw_update(conn, file_name):
    """This function gets the bmc file name and performs the update.
    """
    logging.debug("Update file location %s " %(file_name))
    logging.debug("Warning, the update process takes 3 minutes to complete. " +
            "Please don't turn off the power!!!")
    logging.debug("...")

    # Check if the update files exists.
    conn.sendline('ls '+file_name, "#", timeout=10)
    conn.output = conn.output.split()
    conn.output = conn.output[1]

    if conn.output != file_name:
        logging.debug ("File not found ")
        logging.error(conn.output)
        sys.exit(1)
    else:
        logging.debug("Found file. Performing firmware update.")

    # Update Complete, Please wait for BMC reboot, about 1 or 2 mins
    conn.sendline('/usr/bin/sumtool -c UpdateBmc --file ' +file_name+ ' --overwrite_cfg --overwrite_sdr', "Update Complete", timeout=2000)
    logging.debug("The node is required to be re-booted for the firmware " +
            "update to take effect.")

    # Checking BMC status Done
    conn.sendline('', conn.PROMPT, timeout=200)
    logging.debug("The node update is completed.")
    bmc_set_to_default(conn)

    logging.debug("The node will reboot automatically within 120 seconds.")
    bmc_set_cold_reboot(conn)

''' --------------------------- BMC Update Process --------------------------'''
#@time_elapsed
def check_update_process(conn, part_number, fw_version):
    """ This function checks if the current firmware requires an update, and if
        it is updatable. If the current firmware is updatable return True. The
        function also returns the file name to update.
    """

    try:
        prefer_bmc_version = BMC.BMC_FW_PREFER[part_number]
        logging.debug("expect_ver %s" %(prefer_bmc_version))
        file_name = BMC.BMC_FW_FILES[(part_number, prefer_bmc_version)]
        logging.debug(file_name)
    except KeyError, e:
        logging.error("The version %s is not supported" %part_number)
        sys.exit(1)

    # First check to see if the firmware is the preferred firmware
    if fw_version == prefer_bmc_version:
        logging.info("Current BMC.BMC version "+fw_version+" is matched ")
        # TESTING - Commend out return to ignore the fw prefer check
        return (False, file_name)
    else:
        logging.debug("Version mismatch. Next, checking version in acceptable list")

    # Second check if the current firmware is acceptable
    if is_fw_acceptable(conn, part_number, fw_version):
        logging.info("Current BMC.BMC version "+fw_version+" is acceptable")
        return(False, file_name)
    else:
        logging.debug("Current firmware is not acceptable require the update")
        logging.info("Current BMC.BMC version " + fw_version +
                " is outdated/ un-qualified. Running BMC update process:")

    # Third check if the update is conflict
    logging.debug("Update %s %s %s " %(part_number, fw_version,
            prefer_bmc_version))
    if is_update_conflict(conn, part_number, fw_version, prefer_bmc_version):
        logging.error("Update causes a conflict. Exiting.")
        sys.exit(1)
    else:
        logging.debug("Update does not cause a conflict. Updating")

    return(True, file_name)

'''--------------------------------------------------------------------------'''
def check_support_process(conn, model, version):
    """ This function checks if the forced update option is available. If the
        option is supported, it returns True and the file name to update.
    """
    # Check the version support
    version = str(version)[2:-2]

    try:
        update_part_number = (BMC.fw[model]["BMC"])
        uut_part_number    = get_part_info(conn)
        file_name          = BMC.BMC_FW_FILES[(update_part_number, version)]
    except KeyError, e:
        logging.error("The version %s is not supported" %version)
        sys.exit(1)

    # Check the required update and the on-board part.
    if update_part_number != uut_part_number:
        logging.error("Model %s has different part %s vs %s " %(model,
                update_part_number, uut_part_number))
        sys.exit(1)

    return (True, file_name)

'''--------------------------------------------------------------------------'''
def main():
    model, version = "", ""
    args = parse_args()

    with open(args.log, 'wb') as log:
        try:
            is_logged_in = False
            conn = Connection(logfile=sys.stdout, static_logpath =
                    '~/logs/{0}'.format(this_filename))
            is_logged_in = conn.login(args.ip, args.username, args.password,
                           auto_prompt_reset=False, remove_known_hosts=True,
                           ping_before_connect=False)

            if args.model:
                # Update by force with model and version
                if args.version:
                    (ret_status, ret_file) = check_support_process(conn,
                            args.model, args.version)
                    if ret_status:
                        do_fw_update(conn, ret_file)
                else:
                    logging.error("The option -v <version> required")
                    sys.exit(1)
            else:
                # Update detected items to the node and save to json
                part_number = get_part_info(conn)
                fw_version  = get_part_version(conn)
                (ret_status, ret_file) = check_update_process(conn, part_number,
                        fw_version)
                if ret_status:
                    do_fw_update(conn, ret_file)
                else:
                    logging.debug("Current firmware does not require an " +
                            "update!")
                print("Update Completed!")

            print("BMC update successful!")
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
