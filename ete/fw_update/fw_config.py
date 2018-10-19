#!/usr/bin/env python

"""
Program name:	fw_config.py
Description :
    This file hold all information for the firmware update process.
        - The fw dictionary holds a list of chassises that have the firmware.
        - Each firmware in the list will handle by a script to do the update.
    Each firmware component in the chassis has dictionaries:
         xxx_FW_FILES       : Point to the location of the firmware update files
         xxx_FW_PREFER      : If there is no option to force the update, the update select the prefer.
         xxx_FW_CONFLICT    : List of the firmware that is conflicted with the update firmware.
         xxx_FW_ACCEPTABLE  : List of the current firmware is acceptable.
    The firmware update scripts will handle the update by:
        - Auto detection that checks the current firmware in the chassis to do the update after 
          check it with the prefered firmware, acceptable firmware and confliction firmware.. 
        - Force update requires the inputs of the chassis, the firmware version. Some chassis have
          multiple cards (eg: HBA requires the card order number). 
Tools requirement:
    Linux Tools 
    BMC   :  ipmitool, dmidecode, ipmicfg-linux.x86_64, sumtool
    BIOS  :  ipmitool, dmidecode, sumtool
    HBA   :  ipmitool, sas3flash
    MLX   :  mlxup
    INTC  :  ipmitool, ethtool,   lspci, ip, nvmupdate64e
    MCU   :  ipmicfg-linux.x86_64 


-------------------------------------------------------------------------------
AOC-2UR68-i4G	2U Ultra Riser	15d9	0848	Intel i350-AM4		8086	1521
AOC-2UR66-i4G	2U Ultra Riser	15d9	0875	Intel i350-AM4		8086	1521
AOC-URN2-I2XS	1U Ultra Riser	15d9	0870	Intel 82599ES		8086	10FB
AOC-2UR8N4-i2XT	2U Ultra Riser	15d9	0874	Intel X540		8086	1528
AOC-MTG-i2TM		 SIOM	15d9	0920	Intel X550-AT2		8086	1563
AOC-UR-i2XT	1U Ultra Riser	15d9	085D	Intel X540		8086	1528


"""

import os

# Local host test path
global IMGS_PATH 
global CMD_PATH
IMGS_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/imgs'
CMD_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + '/bin'

# Remote access test path
#IMGS_PATH = "/usr/imgs"
#CMD_PATH  = "/usr/bin"

""" -------------------- Firmware with model G5 ---------------------"""
fw = {
    "NX-1065S-G5": {
        "BMC" : "X10DRT-P",
        "BIOS": "X10DRT-P",
        "HBA" : "SAS3008",
        "MCU" : "BPN-SAS3-827HQ-NI22",
        "MCX312B-XCCT" : "MCX312B-XCC_Ax",
        "MCX314A-BCCT" : "MCX314A-BCC_Ax",
    },

    "NX-6035C-G5" : {
        "HBA" : "SAS3008",
        "MCU" : "BPN-SAS3-827HD2-N4-NI22",
        "MCX314A-BCCT" : "MCX314A-BCC_Ax",
    },

    "NX-1065-G6": {
        "BIOS": "X11DPT-B",
        "BMC" : "X11DPT-B",
        "HBA" : "SAS3008",
        "MCU" : "BPN-SAS3-827BHQ-N3-NI2",
        "AOC-MTG-I2TM-NI22" : "15d9:0920",
        "MCX414A-BCAT" : "MCX414A-BCA_Ax",
    },

    "NX-1175S-G6": {
        "BIOS": "X11DPT-B",
        "BMC" : "X11DPT-B",
        "HBA" : "",
    },

    "NX-3060-G6" : {
        "BIOS": "X11DPT-B",
        "BMC" : "X11DPT-B",
        "HBA" : "SAS3008",
        "MCU" : "BPN-SAS3-217BHQ-N4-NI22",
        "AOC-MTG-I2TM-NI22" : "15d9:0920",
        "MCX4121A-ACAT" : "MCX4121A-ACA_Ax",
        #"MCX414A-BCAT"  : "15b3:0003",
        "MCX414A-BCAT"  : "MCX414A-BCA_Ax",
    },

    "NX-3155G-G6" : {
        "BIOS": "X11DPU",
        "BMC" : "X11DPU",
        "HBA" : "SAS3008",
        "MCX412A-ACAT" : "MCX4121A-ACA_Ax",
        "MCX414A-BCAT" : "MCX414A-BCA_Ax",
    },

    "NX-3170-G6" : {
        "BIOS": "X11DPU",
        "BMC" : "X11DPU",
        "HBA" : "SAS3008",
    },

    "NX-5155-G6" : {
        "BIOS": "X11DPT-B",
        "BMC" : "X11DPT-B",
        "HBA" : "SAS3008",
        "MCX412A-ACAT" : "MCX4121A-ACA_Ax",
        "MCX414A-BCAT" : "MCX414A-BCA_Ax",
    },

    "NX-8035-G6" : {
        "BIOS": "X11DPT-B",
        "BMC" : "X11DPT-B",
        "HBA" : "SAS3008",
        "MCU" : "BPN-SAS3-827BHQ-N3-NI22",
        "AOC-MTG-I2TM-NI22" : "15d9:0920",
        "MCX412A-ACAT" : "MCX4121A-ACA_Ax",
        "MCX414A-BCAT" : "MCX414A-BCA_Ax",
    },

    "NX-8155-G6" : {
        "BIOS": "X11PDU",
        "BMC" : "X11PDU",
        "HBA" : "SAS3008",
        "MCX412A-ACAT" : "MCX4121A-ACA_Ax",
        "MCX414A-BCAT" : "MCX414A-BCA_Ax",
    }
}


""" ----------------------- BMC LIST -------------------------"""

BMC_FW_FILES = dict([
    (("X11DPT-B",    "6.39"),   "%s/bmc/X11DPT-B/NX-G6-639-180122.bin" %IMGS_PATH), 
    (("X11DPU",      "6.43"),   "%s/bmc/X11DPU/NX-G6-643-180206.bin" %IMGS_PATH),
    (("X10SRW",      "3.63"),   "%s/bmc/BMC_G4_G5_3_63/NX-G4G5-3.63-180803.bin" %IMGS_PATH),
    (("X10DRT-P",    "3.63"),   "%s/bmc/BMC_G4_G5_3_63/NX-G4G5-3.63-180803.bin" %IMGS_PATH),
    (("X10DRU-i+",   "3.63"),   "%s/bmc/BMC_G4_G5_3_63/NX-G4G5-3.63-180803.bin" %IMGS_PATH),
])

BMC_FW_CONFLICT = {
    ("X11DPT-B",    "6.39"):    [],
    ("X11DPU" ,     "6.43"):    [],
    ("X10SRW",      "3.63"):    [],
    ("X10DRT-P",    "3.63"):    [],
    ("X10DRU-i+",   "3.63"):    [],
}

BMC_FW_PREFER = dict([
    ("X11DPT-B",    "6.39"), 
    ("X11DPU" ,     "6.43"), 
    ("X10SRW",      "3.63"),
    ("X10DRT-P",    "3.63"),
    ("X10DRU-i+",   "3.63"),
])

BMC_FW_ACCEPTABLE = {
    "X11DPT-B" :    ["6.39"], 
    "X11DPU"   :    ["6.43"], 
    "X10SRW"   :    ["3.63"],
    "X10DRT-P" :    ["3.63"],
    "X10DRU-i+":    ["3.63"],
}

""" ----------------------- BIOS LIST -------------------------"""

"""
In-band  : Read part number and firmware version. 
OO-band  : Read the board-id and date from a test stand.

"""

BIOS_FW_FILES = dict([
    (("X11DPT-B",   "PB20.001"),                  "%s/bios/X11DPT-B/NX11DPTB8.223" %IMGS_PATH),
    (("X11DPU",     "PU11.144"),                  "%s/bios/X11DPU/NX11DPU8.226" %IMGS_PATH),
    (("X10SRW",     "4.0"),                       "%s/bios/X10SRW/NX10SRW8.626" %IMGS_PATH),
    (("X10DRT-P",   "4.0"),                       "%s/bios/X10DRT-P/NX10DRT8.626" %IMGS_PATH),
    (("X10DRU-i+",  "4.0"),                       "%s/bios/X10DRU-i+/NX10DRU8.626" %IMGS_PATH),
])

BIOS_FW_CONFLICT = {
    ("X11DPU",     "PU11.144"):                   [],
    ("X11DPT-B",   "PB20.001"):                   [],
    ("X10SRW",          "4.0"):                   [],
    ("X10DRT-P",        "4.0"):                   [],
    ("X10DRU-i+",       "4.0"):                   [],
}

BIOS_FW_PREFER = dict([
    ("X11DPT-B",   "PB20.001"),
    ("X11DPU",     "PU11.144"),
    ("X10SRW",          "4.0"),
    ("X10DRT-P",        "4.0"),
    ("X10DRU-i+",       "4.0"),
])

BIOS_FW_ACCEPTABLE = {
    "X11DPT-B":   ["PB20.001"],
    "X11DPU"  :   ["PU11.144"],
    "X10SRW"  :        ["4.0"],
    "X10DRT-P":        ["4.0"],
    "X10DRU-i+":       ["4.0"],
}


""" ----------------------- HBA LIST --------------------------"""

HBA_FW_FILES = dict([
    (("SAS3008"   , "14.00.00.00"),                    "%s/hba/14.00.00.00/3008IT14.ROM" %IMGS_PATH),
])

HBA_FW_CONFLICT = {
    ("SAS3008"   ,  "14.00.00.00"):                    [],
}

HBA_FW_PREFER = dict([
    ("SAS3008"   ,  "14.00.00.00"),
])

HBA_FW_ACCEPTABLE = {
    "SAS3008"   :  ["14.00.00.00"],
}


""" ----------------------- MCU LIST --------------------------"""

MCU_FW_FILES = dict([
    (("BPN-SAS3-827HQ-NI22",          "1.40"),		"%s/mcu/g4_g5/1.40/lcmc_1.40_0714.srec" %IMGS_PATH),
    (("BPN-SAS3-217HQ",               "1.08"),		"MCU file name to update"),
    (("BPN-SAS3-827HD2-N4-NI22",      "1.1" ),		"MCU file name to update"),
    (("BPN-SAS3-827HQ2-NI22",         "1.09"),          "MCU file name to update"),
    (("BPN-SAS3-217HD2-N4",           "1.2" ),		"MCU file name to update"),
    (("BPN-SAS3-827BHQ-N3",           "1.15"),		"%s/mcu/g6_g7/1.15/217N4_EC_2017-10-06_1846.45_1.15.bin" %IMGS_PATH),
    (("BPN-SAS3-217BHQ-N4-NI22",      "1.15"),         	"%s/mcu/g6_g7/1.15/217N4_EC_2017-10-06_1846.45_1.15.bin" %IMGS_PATH), 
])

MCU_FW_CONFLICT = {
    ("BPN-SAS3-827HQ-NI22",           "1.40"):          [],
    ("BPN-SAS3-217HQ",                "1.08"):          [],
    ("BPN-SAS3-827HD2-N4-NI22",       "1.1" ):          [],
    ("BPN-SAS3-827HQ2-NI22",          "1.09"):          [],
    ("BPN-SAS3-217HD2-N4",            "1.2" ):          [],
    ("BPN-SAS3-827BHQ-N3",            "1.15"):          [],
    ("BPN-SAS3-217BHQ-N4-NI22",       "1.15"):          [],
}

MCU_FW_PREFER = dict([
    ("BPN-SAS3-827HQ-NI22",           "1.40"),
    ("BPN-SAS3-217HQ",                "1.08"),
    ("BPN-SAS3-827HD2-N4-NI22",       "1.1" ),
    ("BPN-SAS3-827HQ2-NI22",          "1.09"),
    ("BPN-SAS3-217HD2-N4",            "1.2" ),
    ("BPN-SAS3-827BHQ-N3",            "1.15"),
    ("BPN-SAS3-217BHQ-N4-NI22",       "1.15"), 
])

MCU_FW_ACCEPTABLE = {
    "BPN-SAS3-827HQ-NI22":            ["1.40"],
    "BPN-SAS3-217HQ":                 ["1.08"],
    "BPN-SAS3-827HD2-N4-NI22":        ["1.1" ],
    "BPN-SAS3-827HQ2-NI22":           ["1.09"],
    "BPN-SAS3-217HD2-N4":             ["1.2" ],
    "BPN-SAS3-827BHQ-N3":             ["1.15"],
    "BPN-SAS3-217BHQ-N4-NI22":        ["1.15"],
}


""" ----------------------- NIC LIST --------------------------"""

NIC_FW_FILES = dict([
    (("MCX4121A-ACA_Ax",   "14.20.1010"), "%s/net/mlx/fw-ConnectX4Lx-rel-14_20_1010-MCX4121A-ACA_Ax-FlexBoot-3.5.210.bin" %IMGS_PATH),
    (("MCX414A-BCA_Ax",    "12.20.1010"), "%s/net/mlx/fw-ConnectX4-rel-12_20_1010-MCX414A-BCA_Ax-FlexBoot-3.5.210.bin" %IMGS_PATH),
    (("MCX312B-XCC_Ax",     "2.42.5000"), "%s/net/mlx/fw-ConnectX3Pro-rel-2_42_5000-MCX312B-XCC_Ax-FlexBoot-3.4.572.bin" %IMGS_PATH),
    (("MCX312A-XCB_A2-A6",  "2.36.5150"), "%s/net/mlx/fw-ConnectX3Pro-rel-2_36_5150-MCX312B-XCC_Ax-FlexBoot-3.4.740.bin" %IMGS_PATH),
    (("15d9:0920",         "0x80000aee"), "%s/net/intc/0x80000aee/nvmupdate.cfg" %IMGS_PATH),
    (("8086:000c",         "0x800007cb"), "%s/net/intc/0x800007cb/nvmupdate.cfg" %IMGS_PATH),
    (("15b3:0003",         "14.20.1010"), "%s/net/mlx/fw-ConnectX4Lx-rel-14_20_1010-MCX4121A-ACA_Ax-FlexBoot-3.5.210.bin" %IMGS_PATH),
    (("15d9:0848",         "          "), "%s/net/intc/" %IMGS_PATH),
    (("15d9:0875",         "          "), "%s/net/intc/" %IMGS_PATH),
    (("15d9:0870",         "          "), "%s/net/intc/" %IMGS_PATH),
    (("15d9:085D",         "          "), "%s/net/intc/" %IMGS_PATH),
    (("15d9:0874",         "          "), "%s/net/intc/" %IMGS_PATH),
])

NIC_FW_CONFLICT = {
    ("MCX4121A-ACA_Ax",    "14.20.1010"):    [],
    ("MCX414A-BCA_Ax",     "12.20.1010"):    [],
    ("MCX312B-XCB_A2-A6",   "2.42.5000"):    [],
    ("MCX312B-XCC_Ax",      "2.36.5150"):    [],
    ("15d9:0920",          "0x80000aee"):    [],
    ("8086:000c",          "0x800007cb"):    [],
    ("15b3:0003",          "14.20.1010"):    [],
    ("15d9:0848",          "          "):    [],
    ("15d9:0875",          "          "):    [],
    ("15d9:0870",          "          "):    [],
    ("15d9:085D",          "          "):    [],
    ("15d9:0874",          "          "):    [],
}

NIC_FW_PREFER = dict([
    ("MCX4121A-ACA_Ax",    "14.20.1010"),
    ("MCX414A-BCA_Ax",     "12.20.1010"),
    ("MCX312B-XCC_A2-A6",   "2.42.5000"),
    ("MCX312B-XCC_Ax",      "2.36.5150"),
    ("15d9:0920",          "0x80000aee"),
    ("8086:000c",          "0x800007cb"),
    ("15b3:0003",          "14.20.1010"),
    ("15d9:0848",          ""),
    ("15d9:0875",          ""),
    ("15d9:0870",          ""),
    ("15d9:085D",          ""),
    ("15d9:0874",          ""),
])

NIC_FW_ACCEPTABLE = {
    "MCX4121A-ACA_Ax":    ["14.20.1010"],
    "MCX414A-BCA_Ax":     ["12.20.1010"],
    "MCX312B-XCB_A2-A6":  [ "2.42.5000"],
    "MCX312B-XCC_Ax":     [ "2.36.5150"],
    "15d9:0920":          ["0x800007f6", "0x80000a73", "0x80000aee"],
    "8086:000c":          ["0x800007cb"],
    "15b3:0003":          ["14.20.1010"],
    "15d9:0848":          [" "],
    "15d9:0875":          [" "],
    "15d9:0870":          [" "],
    "15d9:085D":          [" "],
    "15d9:0874":          [" "],
}

NIC_CHIPSET = {
    "INTC" : ["15d9:0920", "8086:000c", "15b3:0003", "15d9:0848", "15d9:0875", "15d9:0870", "15d9:085D", "15d9:0874"],
    "MLX"  : ["15b3:0003"],
}
