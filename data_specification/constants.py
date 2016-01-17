"""
Constants used by the Data Structure Generator (DSG)
and the Spec Executor
"""

# MAGIC Numbers:
DSG_MAGIC_NUM     = 0x5B7CA17E  # Data spec magic number
APPDATA_MAGIC_NUM = 0xAD130AD6  # Application datafile magic number
DSE_VERSION       = 0x00010000  # Version of the file produced by the DSE

# DSG Arrays and tables sizes:
MAX_REGISTERS       = 16
MAX_MEM_REGIONS     = 16
MAX_STRUCT_SLOTS    = 16
MAX_STRUCT_ELEMENTS = 255
MAX_PACKSPEC_SLOTS  = 16
MAX_CONSTRUCTORS    = 16
MAX_PARAM_LISTS     = 16
MAX_RNGS            = 16
MAX_RANDOM_DISTS    = 16

APP_PTR_TABLE_HEADER_BYTE_SIZE = 8
APP_PTR_TABLE_BYTE_SIZE = APP_PTR_TABLE_HEADER_BYTE_SIZE + MAX_MEM_REGIONS * 4

# Constants used by DSG command encoding:
LEN1, LEN2, LEN3, LEN4 = 0, 1, 2, 3
NO_REGS, DEST_ONLY, SRC1_ONLY, SRC1_AND_SRC2, DEST_AND_SRC1, ALL_REGS = \
                                                               0, 4, 2, 3, 6, 7

# return values from functions of the data spec executor
END_SPEC_EXECUTOR = -1
