import struct

from data_specification.data_specification_executor_functions \
    import DataSpecificationExecutorFunctions as Dsef
from data_specification import exceptions, constants
from data_specification.enums import commands

import traceback


class DataSpecificationExecutor(object):
    """ Used to execute a data specification language file to produce a memory\
        image
    """

    __slots__ = [
        # The object to read the specification language file
        "spec_reader",

        # The object to write the memory image to
        "mem_writer",

        # The object to write the report of the data specification executor
        "report_writer",

        # The amount of space used by the dsg script.
        "space_used",

        # the amount of space written by the dsg script (different from used,
        # as empty data regions are not counted as written)
        "space_written",

        # ???????????
        "dsef"

    ]

    def __init__(self, spec_reader, mem_writer, memory_space,
                 report_writer=None):
        """
        :param spec_reader: The object to read the specification language file\
                    from
        :type spec_reader:\
                    :py:class:`data_specification.abstract_data_reader.\
                    AbstractDataReader`
        :param mem_writer: The object to write the memory image to
        :type mem_writer:\
                    :py:class:`data_specification.abstract_data_writer.
                    AbstractDataWriter`
        :param memory_space: memory available on the destination architecture
        :type memory_space: int
        :param report_writer: The object to write the report of the data \
                    specification executor
        :type report_writer:\
                    :py:class:`data_specification.abstract_data_writer.
                    AbstractDataWriter`
        :raise spinn_storage_handlers.exceptions.DataReadException:\
                    If a read from external storage fails
        :raise spinn_storage_handlers.exceptions.DataWriteException:\
                    If a write to external storage fails
        """
        self.spec_reader = spec_reader
        self.mem_writer = mem_writer
        self.report_writer = report_writer
        self.space_used = 0
        self.space_written = 0
        self.dsef = Dsef(self.spec_reader, self.mem_writer, memory_space)

    def execute(self):
        """ Executes the specification

        :return: The number of bytes used by the image and \
                the number of bytes written by the image
        :rtype: int
        :raise spinn_storage_handlers.exceptions.DataReadException:\
                    If a read from external storage fails
        :raise spinn_storage_handlers.exceptions.DataWriteException:\
                    If a write to external storage fails
        :raise data_specification.exceptions.DataSpecificationException:\
                    If there is an error when executing the specification
        :raise data_specification.exceptions.\
                    DataSpecificationTablePointerOutOfMemory:\
                    If the table pointer generated as data header exceeds the \
                    size of the available memory
        """
        instruction_spec = self.spec_reader.read(4)
        while len(instruction_spec) != 0:
            # process the received command
            cmd = struct.unpack("<I", str(instruction_spec))[0]

            opcode = (cmd >> 20) & 0xFF

            try:
                # noinspection PyArgumentList
                return_value = \
                    commands.Commands(opcode).exec_function(self.dsef, cmd)
            except ValueError:
                traceback.print_exc()
                raise exceptions.DataSpecificationException(
                    "Invalid command 0x{0:X} while reading file {1:s}".format(
                        cmd, self.spec_reader.filename))
            except TypeError:
                traceback.print_exc()
                raise exceptions.DataSpecificationException(
                    "Invalid command 0x{0:X} while reading file {1:s}".format(
                        cmd, self.spec_reader.filename))

            if return_value == constants.END_SPEC_EXECUTOR:
                break
            instruction_spec = self.spec_reader.read(4)

    def write_dse_output_file(self, start_address=0):
        """ Writes the file generated by the DSE given a location start\
            address where the file will be written

        :param start_address: starting address of the region of memory where\
                    this application data file is going to be stored
        :type start_address: unsigned int
        :rtype: None:
        """
        # write the data file header
        self.write_header()

        # write the table pointer
        self.write_pointer_table(start_address)

        # take into account what has just been written to file
        self.space_written = self.space_used

        # write the data from dsef.mem_regions previously computed
        for i in xrange(constants.MAX_MEM_REGIONS):
            memory_region = self.dsef.mem_regions[i]
            if memory_region is not None:
                if ((memory_region.unfilled and
                    self.dsef.mem_regions.needs_to_write_region(i)) or
                        not memory_region.unfilled):
                    max_pointer = memory_region.max_write_pointer
                    if not memory_region.shrink or memory_region.unfilled:
                        max_pointer = memory_region.allocated_size
                    self.mem_writer.write(memory_region.region_data[
                        :max_pointer])
                self.space_written -= memory_region.allocated_size

    def write_dse_region_output_file(self, region_to_write):
        """ supports writing a specific region instead of the entire DSE file

        :param region_to_write: the dsg region to write
        :rtype: int
        """
        memory_region = self.dsef.mem_regions[region_to_write]
        if memory_region is not None:
            self.mem_writer.write(
                memory_region.region_data[:memory_region.max_write_pointer])
            return memory_region.max_write_pointer
        return 0

    def get_region(self, region_id):
        """ Get a region with a given id

        :param region_id: The id of the region to get
        :type region_id: int
        :return: The region, or None if the region was not allocated
        """
        return self.dsef.mem_regions[region_id]

    def write_header(self):
        """ writes the DSE header which resides at the top of any cores\
            memory region when used with a DSE.

        :rtype: None
        """
        if self.report_writer is not None:
            self.report_writer.write("header structure \n")
        magic_number_encoded = bytearray(
            struct.pack("<I", constants.APPDATA_MAGIC_NUM))

        if self.report_writer is not None:
            self.report_writer.write(
                "{} Magic number - file identifier: {} \n".format(
                    self.mem_writer.tell(), constants.APPDATA_MAGIC_NUM))
        self.mem_writer.write(magic_number_encoded)

        version_encoded = bytearray(struct.pack("<I", constants.DSE_VERSION))
        if self.report_writer is not None:
            self.report_writer.write(
                "{} File structure version: {} \n".format(
                    self.mem_writer.tell(), constants.DSE_VERSION))
        self.mem_writer.write(version_encoded)

        self.space_used = 0

    def write_pointer_table(self, start_address):
        """ writes the pointer table which defines at what memory address\
            each memory region starts at as well as the size of each region

        :param start_address: starting address of the region of memory where\
                    this application data file is going to be stored
        :type start_address: unsigned int
        :rtype: None
        """
        if self.report_writer is not None:
            self.report_writer.write("Pointer table \n")
        pointer_table = [0] * constants.MAX_MEM_REGIONS
        pointer_table_size = constants.MAX_MEM_REGIONS * 4
        self.space_used += \
            pointer_table_size + constants.APP_PTR_TABLE_HEADER_BYTE_SIZE
        next_free_offset = \
            pointer_table_size + constants.APP_PTR_TABLE_HEADER_BYTE_SIZE

        for i in xrange(constants.MAX_MEM_REGIONS):
            memory_region = self.dsef.mem_regions[i]
            if memory_region is not None:
                pointer_table[i] = next_free_offset + start_address
                if memory_region.unfilled or not memory_region.shrink:
                    region_size = memory_region.allocated_size
                else:
                    region_size = memory_region.max_write_pointer
            else:
                pointer_table[i] = 0
                region_size = 0
            self.space_used += region_size
            next_free_offset += region_size

        index = 0
        for i in pointer_table:
            if self.report_writer is not None:
                self.report_writer.write(
                    "{:8X} pointer {:d}: {:8X} \n".format(
                        self.mem_writer.tell(), index, i))
            encoded_pointer = struct.pack("<I", i)
            self.mem_writer.write(encoded_pointer)
            index += 1

        if self.report_writer is not None:
            self.report_writer.write("End of pointer table \n")

    def get_constructed_data_size(self):
        """ Return the size of the data that will be written to memory

        :return: size of the data that will be written to memory
        :rtype: unsigned int
        """
        size = constants.APP_PTR_TABLE_BYTE_SIZE
        for i in xrange(constants.MAX_MEM_REGIONS):
            memory_region = self.dsef.mem_regions[i]
            if memory_region is not None:
                size += memory_region.allocated_size
        return size
