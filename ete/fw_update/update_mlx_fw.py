#!/usr/local/bin/python2.7
'''update_mlx_fw.py

This utility helps to check the mlx firmweware version on the model..
If the firmware is out of date, it will update with the prefer one from the "fw_config.py".
The utility saves all logs in uut_logs.

The script also has the options to force the update:

Prerequisites:
    - This module is tested on Python 2.7.15 and is compatible with python
      2.7 or later.

Usage:
    $ ./update_mlx_fw.py -h
    $ python update_mlx_fw.py -h
    usage: update_mlx_fw.py [-h] [-f path/firmware] [-l LOG] [--username USERNAME] \
                     [--password PASSWORD] [--ip IP] [-m model] [-f file name to update]

    MLX Firmware Update

    optional arguments:
      -h, --help            show this help message and exit
      -l LOG, --log LOG     Specify the log filename to be saved as
      --username USERNAME   username
      --password PASSWORD   password
      --ip IP               Destination IP to collect information on
      -m                    Model
      -p                    Part Number
      -v                    MLX path/version

Examples:
    Update the MLX on the local system without a specify file:
        python update_mlx_fw.py
        ./update_mlx_fw.py

    Update the MLX on the local with the model NX-8036-G6 specify part MCX414A-BCAT firmware 12.20.1010
        python update_mlx_fw.py -m NX-8036-G6 -p MCX414A-BCAT -v 12.20.1010
        ./update_mlx_fw.py -m NX-8036-G6 -p MCX414A-BCAT -v 12.20.1010

    Update MLX firmware on the remote system with the ip=192.168.2.123 input for the host:
        python update_mlx_fw.py --ip=192.168.2.123
        ./update_mlx_fw.py --ip=192.168.2.123

    Update the MLX on the remote ip=192.168.2.123 with the model NX-8036-G6 specify mlx firmware "12.20.1010"  :
        python update_mlx_fw.py --ip=192.168.2.123 -m NX-3060-G6 -p MCX414A-BCAT -v 12.20.1010
        ./update_mlx_fw.py --ip=192.168.2.123 -m NX-8036-G6 -p MCX414A-BCAT -v 12.20.1010

    Retrieve the specify filename for the log:
        python update_mlx_fw.py --ip=192.168.2.123 -l=sn123_update_mlx_fw.log
        ./update_mlx_fw.py --log=sn123_update_mlx_fw.log

    Retrieve the specify filename for the json:
        python update_mlx_fw.py --ip=192.168.2.123 -j=node_sn.json
        ./update_mlx_fw.py --json=node_sn.json

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
import fw_config as NIC

#logging.basicConfig(filename="debug_mlx_fw.log", level=logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)

this_filename = os.path.basename(__file__).split('.')[0]

def parse_args():
    '''This function parses and return arguments parse in'''
    parser = argparse.ArgumentParser(
        description='This parse get all input options to do the MLX update')
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
        help='Destination IP to collect information on', default='localhost')
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
    fru = {}

    # Get FRU info if it does not exist
    conn.sendline('ipmitool fru', conn.PROMPT)
    if conn.output:
        for line in conn.output.split('\n')[1:]:
            if ' : ' in line:
                k, v = line.split(' : ', 1)
                fru[k.strip()] = v.strip()
    else:
        print('ERROR: ipmitool fru command returns nothing!')
        sys.exit(1)

    if verbose:
        print(json.dumps(fru, indent=4))
    return fru

''' ----------------------------- BOARD_ID-----------------------------------'''
@time_elapsed
def get_mlx_part_number(conn, verbose=False):
    ''' Get MLX part number'''

    CMD="%s/mlxup -query" %NIC.CMD_PATH
    conn.sendline(CMD, conn.PROMPT)
    if conn.output:
        print(conn.output)
        mlx_detect = re.search(r'MCX(.+)\S+', conn.output, re.I|re.M)
        if mlx_detect:
            logging.debug("Mellanox card detected")
        else:
            logging.error("No Mellanox card detected")
            exit(1)
        mlx_part_number = mlx_detect.group()

    if verbose:
        logging.debug(json.dumps(mlx_part_number, indent=4))

    return mlx_part_number

''' ----------------------------- MLX_VERSION ------------------------------'''
@time_elapsed
def get_mlx_version(conn, verbose=False):
    # Get mlx version
    CMD="%s/mlxup -query" %NIC.CMD_PATH
    conn.sendline(CMD, conn.PROMPT)
    if conn.output:
        logging.debug(conn.output)
        mlx_obj = re.search(r'[F][W]\s+\d+[.]\d+[.]\d+', conn.output, re.I|re.M)
        logging.debug(mlx_obj.group())
        mlx_version = mlx_obj.group()
        if mlx_version:
            mlx_obj = re.search(r'\d+[.]\d+[.]\d+', mlx_version)
            logging.debug(mlx_obj.group())
            mlx_version = mlx_obj.group()

    if verbose:
        logging.debug(json.dumps(mlx_version, indent=4))

    return mlx_version

''' --------------------------- Check MLX FW Acceptable --------------------'''
@time_elapsed
def is_fw_acceptable(conn, mlx_part_number, mlx_version, verbose=False):
    '''Check if the mlx reading from the baseboard is acceptable.
       if the firmware is in the list of acceptible, it returns True  '''

    if (mlx_version in NIC.NIC_FW_ACCEPTABLE[mlx_part_number]):
        logging.debug("mlx firmware Version: %s is acceptable" %mlx_version)
        return True
    else:
        logging.debug("mlx firmwere Version: %s is not acceptable that requires to update." %mlx_version)
        return False

''' --------------------- Check MLX FW Update Conflict --------------------'''
@time_elapsed
def is_update_conflict(conn, mlx_part_number, mlx_version, prefer_mlx_version, verbose=False):
    '''
    Check if the mlx version on the board will be conflicted if we update to the prefer one.
    if the update conflict, it return True
    '''
    if (mlx_version in NIC.NIC_FW_CONFLICT[(mlx_part_number, prefer_mlx_version)]):
        logging.debug("mlx version update from Version: % to Version: % will be conflicted" %(mlx_version, prefer_mlx_version))
        return True
    else:
        logging.debug("mlx update iis not conflicted")
        return False

""" ----------------------------- do_fw_update --------------------------------------"""
@time_elapsed
def do_fw_update(conn, file_name):
    '''
    Get the mlx file name and do the update.
    '''
    # Check if the update files exists.
    conn.sendline('ls '+file_name, "#", timeout=10)
    print(conn.output)

    conn.output = conn.output.split()
    print(conn.output)
    conn.output = conn.output[1]+conn.output[2]
    print(len(conn.output))
    print(len(file_name))

    print("%s = %s " %(conn.output, file_name))
    if conn.output != file_name:
        logging.error("File not found ")
        logging.debug(conn.output)
        exit(1)
    else:
        logging.debug("Found file do firmware update")

    CMD="%s/mlxup -i " %NIC.CMD_PATH
    OPTS=' -f -u '
    logging.debug("warning, the update process takes 3 minutes to complete. Please don't turn off the power!!!")
    logging.debug("...")

    # Update Complete, Please wait for MLX reboot, about 1 or 2 mins
    conn.sendline(CMD + file_name + OPTS, "#", timeout=200)
    print(conn.output)
    success = re.search(r'Done', conn.output, re.I|re.M)
    if success:
        logging.debug("The node required to re-boot to take the firmware update effect.")
    else:
        print(conn.output)
        logging.error("Fail : Flash write failed")
        exit(1)
    #conn.sendline(CMD + file_name + OPTS, "conn.PROMPT", timeout=200)
    #logging.debug("The node required to re-boot to take the firmware update effect.")

    # Checking MLX status Done
    conn.sendline('', conn.PROMPT, timeout=200)
    logging.debug("The node update completed.")
    
''' --------------------------- MLX Update Process -------------------------'''
@time_elapsed
def check_update_process(conn, part_number, fw_version):

    logging.debug(part_number)
    print(len(part_number))
    prefer_mlx_version = NIC.NIC_FW_PREFER[part_number]
    logging.debug("expect_ver %s" %(prefer_mlx_version))

    file_name = NIC.NIC_FW_FILES[(part_number, prefer_mlx_version)]
    logging.debug(file_name)

    # First check for the same prefer firmware
    if fw_version == prefer_mlx_version:
        logging.debug("Version match")
        logging.info("Current NIC.NIC version "+fw_version+" is matched ")

        #TESTING - Comment out the return to force update
        #return 1
    else:
        logging.debug("Version mis-match. Check for the acceptable list")


    # Second check if the MLX.NIC is acceptable
    if is_fw_acceptable(conn, part_number, fw_version):
        logging.debug("it is acceptible")
        logging.info("Current NIC.NIC version "+fw_version+" is acceptable")

        #TESTING - Comment out the return to force update
        #return 1
    else:
        logging.debug("Firmware is not acceptable require the update")
        logging.info("Current NIC.NIC version "+fw_version+" is outdated/ un-qualified. Running MLX update process:")


    # Third check if the update is conflict
    if is_update_conflict(conn, part_number, fw_version, prefer_mlx_version):
        logging.error("The current firmware is conflicted with the update one so exit")
        exit(1)
    else:
        logging.debug("It is not conflicted so update .....")

    return (True, file_name)

'''-------------------------------------------------------------------------'''
def check_support_process(conn, model, part, version):
    # Check if the option to force update

    # Check version support
    part    = str(part)[2:-2]
    version = str(version)[2:-2]

    try:        
        update_part_number = (NIC.fw[model][part])
        uut_part_number    = get_mlx_part_number(conn)
        file_name          = NIC.NIC_FW_FILES[(update_part_number, version)]
    except KeyError, e:
        logging.error("The version %s is not supported" %version)
        exit(1)

    # Check the required update and the on-board part.
    if update_part_number != uut_part_number:
        logging.error("Model %s has different part %s vs %s " %(model, update_part_number, uut_part_number))
        exit(1)

    return (True, file_name)

'''-------------------------------------------------------------------------'''
def main():
    model, version = "", ""
    args = parse_args()
    
    with open(args.log, 'wb') as log:
        try:
            is_logged_in = False
            conn = Connection(logfile=sys.stdout, static_logpath='~/logs/{0}'.format(this_filename))
            is_logged_in = conn.login(args.ip, args.username, args.password, 
                           auto_prompt_reset=False, remove_known_hosts=True, ping_before_connect=False)

            if args.model:
                # Update by force with model and version/file
                if args.part:
                # Require part for NIC due to multiple cards
                    if args.version:
                        (ret_status, ret_file) = check_support_process(conn, args.model, args.part, 
                                                                       args.version)
                        if ret_status:
                            do_fw_update(conn, ret_file)
            else:
                # Update detected items to the node and save to json
                part_number = get_mlx_part_number(conn)
                fw_version  = get_mlx_version(conn)
                (ret_status, ret_file) = check_update_process(conn, part_number, fw_version)
                if ret_status:
                    do_fw_update(conn, ret_file)
                else:
                    logging.debug("Current firmware not requird update!")

            print("MLX Update Successful!")
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
