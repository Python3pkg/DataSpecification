import unittest
import struct
from io import BytesIO
from io import StringIO

from data_specification import constants
from data_specification.exceptions \
    import DataSpecificationTypeMismatchException,\
    DataSpecificationParameterOutOfBoundsException,\
    DataSpecificationRegionInUseException,\
    DataSpecificationNotAllocatedException,\
    DataSpecificationStructureInUseException,\
    DataSpecificationInvalidOperationException,\
    DataSpecificationNoRegionSelectedException,\
    DataSpecificationInvalidCommandException,\
    DataSpecificationWrongParameterNumberException,\
    DataSpecificationDuplicateParameterException,\
    DataSpecificationFunctionInUse,\
    DataSpecificationRegionUnfilledException,\
    DataSpecificationRandomNumberDistributionInUseException,\
    DataSpecificationRNGInUseException

from data_specification.enums.data_type import DataType
from data_specification.enums.condition import Condition
from data_specification.enums.random_number_generator \
    import RandomNumberGenerator
from data_specification.enums.arithemetic_operation import ArithmeticOperation
from data_specification.enums.logic_operation import LogicOperation
from data_specification.data_specification_generator \
    import DataSpecificationGenerator


class TestDataSpecGeneration(unittest.TestCase):
    def setUp(self):
        # Indicate if there has been a previous read
        self.previous_read = False

        self.spec_writer = BytesIO()
        self.report_writer = StringIO()
        self.dsg = DataSpecificationGenerator(self.spec_writer,
                                              self.report_writer)

    def tearDown(self):
        pass

    def get_next_word(self, count=1):
        if not self.previous_read:
            self.spec_writer.seek(0)
            self.previous_read = True
        if count < 2:
            return struct.unpack("<I", self.spec_writer.read(4))[0]
        words = list()
        for _ in range(count):
            words.append(struct.unpack("<I", self.spec_writer.read(4))[0])
        return words

    def skip_words(self, words):
        if not self.previous_read:
            self.spec_writer.seek(0)
            self.previous_read = True
        self.spec_writer.read(4 * words)

    def test_new_data_spec_generator(self):
        # DSG spec writer not initialized correctly
        # DSG report writer not initialized correctly
        self.assertEqual(self.dsg.spec_writer, self.spec_writer)

        # DSG instruction counter not initialized correctly
        self.assertEqual(self.dsg.report_writer, self.report_writer)

        # DSG memory slots not initialized correctly
        self.assertEqual(self.dsg.instruction_counter, 0)

        # DSG constructor slots not initialized correctly
        self.assertEqual(self.dsg.mem_slot, constants.MAX_MEM_REGIONS * [0])

        # BREAK wrong command word
        self.assertEqual(self.dsg.function, constants.MAX_CONSTRUCTORS * [0])

    def test_define_break(self):
        self.dsg.define_break()
        # BREAK added more words
        self.assertEqual(self.get_next_word(), 0x00000000)
        # NOP wrong command word
        self.assertEqual(self.spec_writer.read(1), "")

    def test_no_operation(self):
        self.dsg.no_operation()
        # NOP added more words
        self.assertEqual(self.get_next_word(), 0x00100000)
        # RESERVE wrong command word for memory region 1
        self.assertEqual(self.spec_writer.read(1), "")

    def test_reserve_memory_region(self):
        self.dsg.reserve_memory_region(1, 0x111)
        self.dsg.reserve_memory_region(2, 0x1122)
        self.dsg.reserve_memory_region(3, 0x1122, empty=True)
        self.dsg.reserve_memory_region(4, 0x3344, label='test')

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.reserve_memory_region(-1, 0x100)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.reserve_memory_region(constants.MAX_MEM_REGIONS, 0x100)
        with self.assertRaises(DataSpecificationRegionInUseException):
            self.dsg.reserve_memory_region(1, 0x100)

        # RESERVE for memory region 1
        self.assertEqual(self.get_next_word(2), [0x10200041, 0x111])
        # RESERVE for memory region 2
        self.assertEqual(self.get_next_word(2), [0x10200042, 0x1122])
        # RESERVE for memory region 3
        self.assertEqual(self.get_next_word(2), [0x102000C3, 0x1122])
        # RESERVE for memory region 4
        self.assertEqual(self.get_next_word(2), [0x10200044, 0x3344])
        # Memory region 1 DSG data wrong
        self.assertEqual(self.dsg.mem_slot[1], [0x111, None, False])
        # Memory region 2 DSG data wrong
        self.assertEqual(self.dsg.mem_slot[2], [0x1122, None, False])
        # Memory region 3 DSG data wrong
        self.assertEqual(self.dsg.mem_slot[3], [0x1122, None, True])
        # FREE wrong command word
        self.assertEqual(self.dsg.mem_slot[4], [0x3344, "test", False])

    def test_free_memory_region(self):
        self.dsg.reserve_memory_region(1, 0x111)
        self.dsg.free_memory_region(1)

        self.skip_words(2)
        # FREE not cleared mem slot entry
        # START_STRUCT
        self.assertEqual(self.get_next_word(), 0x00300001)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.free_memory_region(-1)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.free_memory_region(constants.MAX_MEM_REGIONS)
        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.free_memory_region(2)
        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.free_memory_region(1)
        self.assertEqual(self.dsg.mem_slot[1], 0)

    def test_define_structure(self):
        self.dsg.define_structure(0, [("first", DataType.UINT8, 0xAB)])
        self.dsg.define_structure(1, [("first", DataType.UINT8, 0xAB),
                                      ("second", DataType.UINT32, 0x12345679),
                                      ("third", DataType.INT16, None),
                                      ("fourth", DataType.UINT64,
                                       0x123456789ABCDEF)])
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.define_structure(-1, [("first", DataType.UINT8, 0xAB)])
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.define_structure(constants.MAX_STRUCT_SLOTS,
                                      [("first", DataType.UINT8, 0xAB)])
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.define_structure(1, [])
        with self.assertRaises(DataSpecificationStructureInUseException):
            self.dsg.define_structure(0, [("first", DataType.UINT8, 0xAB)])

        # STRUCT_ELEM
        self.assertEqual(self.get_next_word(), 0x01000000)
        self.assertEqual(self.get_next_word(2), [0x11100000, 0x000000AB])
        self.assertEqual(self.get_next_word(), 0x01200000)
        self.assertEqual(self.get_next_word(), 0x01000001)
        self.assertEqual(self.get_next_word(2), [0x11100000, 0x000000AB])
        self.assertEqual(self.get_next_word(2), [0x11100002, 0x12345679])
        self.assertEqual(self.get_next_word(), 0x01100005)
        self.assertEqual(self.get_next_word(3),
                         [0x21100003, 0x89ABCDEF, 0x01234567])
        # Call addition signed and unsigned
        self.assertEqual(self.get_next_word(), 0x01200000)

    def test_call_arithmetic_operation(self):
        self.dsg.call_arithmetic_operation(2, 0x12, ArithmeticOperation.ADD,
                                           0x34, False, False, False)
        self.dsg.call_arithmetic_operation(2, 0x1234, ArithmeticOperation.ADD,
                                           0x5678, True, False, False)

        # Call subtraction signed and unsigned
        self.dsg.call_arithmetic_operation(3, 0x1234,
                                           ArithmeticOperation.SUBTRACT,
                                           0x3456, False, False, False)
        self.dsg.call_arithmetic_operation(3, 0x1234,
                                           ArithmeticOperation.SUBTRACT,
                                           0x3456, True, False, False)

        # Call multiplication signed and unsigned
        self.dsg.call_arithmetic_operation(3, 0x12345678,
                                           ArithmeticOperation.MULTIPLY,
                                           0x3456, False, False, False)
        self.dsg.call_arithmetic_operation(3, 0x1234,
                                           ArithmeticOperation.MULTIPLY,
                                           0x3456ABCD, True, False, False)

        # Call with register arguments
        self.dsg.call_arithmetic_operation(3, 1, ArithmeticOperation.ADD,
                                           0x3456, False, True, False)
        self.dsg.call_arithmetic_operation(3, 1, ArithmeticOperation.ADD,
                                           2, False, False, True)
        self.dsg.call_arithmetic_operation(3, 3, ArithmeticOperation.ADD,
                                           4, False, True, True)
        self.dsg.call_arithmetic_operation(3, 3, ArithmeticOperation.MULTIPLY,
                                           4, False, True, True)
        self.dsg.call_arithmetic_operation(3, 3, ArithmeticOperation.MULTIPLY,
                                           4, True, True, True)

        # Call exception raise for register values out of bounds
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.call_arithmetic_operation(-1, 0x12,
                                               ArithmeticOperation.ADD,
                                               0x34, True, True, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.call_arithmetic_operation(constants.MAX_REGISTERS, 0x12,
                                               ArithmeticOperation.ADD,
                                               0x34, True, True, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.call_arithmetic_operation(1, -1, ArithmeticOperation.ADD,
                                               0x34, True, True, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.call_arithmetic_operation(1, constants.MAX_REGISTERS,
                                               ArithmeticOperation.ADD, 2,
                                               False, True, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.call_arithmetic_operation(1, 5,
                                               ArithmeticOperation.SUBTRACT,
                                               -1, False, False, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.call_arithmetic_operation(1, 1,
                                               ArithmeticOperation.SUBTRACT,
                                               constants.MAX_REGISTERS,
                                               False, True, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.call_arithmetic_operation(1, 0x1,
                                               ArithmeticOperation.SUBTRACT,
                                               -1, False, False, True)
        # Test unknown type exception raise
        with self.assertRaises(DataSpecificationInvalidOperationException):
            self.dsg.call_arithmetic_operation(1, 1, LogicOperation.OR,
                                               2, 1, False)

        # ARITH_OP
        self.assertEqual(self.get_next_word(3), [0x26742000, 0x12, 0x34])
        self.assertEqual(self.get_next_word(3), [0x267C2000, 0x1234, 0x5678])
        self.assertEqual(self.get_next_word(3), [0x26743001, 0x1234, 0x3456])
        self.assertEqual(self.get_next_word(3), [0x267C3001, 0x1234, 0x3456])
        self.assertEqual(self.get_next_word(3),
                         [0x26743002, 0x12345678, 0x3456])
        self.assertEqual(self.get_next_word(3),
                         [0x267C3002, 0x1234, 0x3456ABCD])
        self.assertEqual(self.get_next_word(2), [0x16763100, 0x3456])
        self.assertEqual(self.get_next_word(2), [0x16753020, 0x1])
        self.assertEqual(self.get_next_word(), 0x06773340)
        self.assertEqual(self.get_next_word(), 0x06773342)
        self.assertEqual(self.get_next_word(), 0x067F3342)

    def test_align_write_pointer(self):
        # Test DataSpecificationNoRegionSelectedException raise
        with self.assertRaises(DataSpecificationNoRegionSelectedException):
            self.dsg.align_write_pointer(1)

        # Define a memory region and switch focus to it
        self.dsg.reserve_memory_region(1, 100)
        self.dsg.switch_write_focus(1)

        # Call align_write_pointer with different parameters
        self.dsg.align_write_pointer(1, False, None)
        self.dsg.align_write_pointer(31, False,  None)
        self.dsg.align_write_pointer(5, True,  None)

        self.dsg.align_write_pointer(1, False, 2)
        self.dsg.align_write_pointer(5, True, 3)

        # Test DataSpecificationOutOfBoundsException raise
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.align_write_pointer(-1)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.align_write_pointer(33)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.align_write_pointer(-1, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.align_write_pointer(constants.MAX_REGISTERS, True)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.align_write_pointer(1, False, -1)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.align_write_pointer(1, False, constants.MAX_REGISTERS)

        self.skip_words(3)
        # WRITE_POINTER
        self.assertEqual(self.get_next_word(), 0x06500001)
        self.assertEqual(self.get_next_word(), 0x0650001F)
        self.assertEqual(self.get_next_word(), 0x06520500)
        self.assertEqual(self.get_next_word(), 0x06542001)
        self.assertEqual(self.get_next_word(), 0x06563500)

    def test_break_loop(self):
        with self.assertRaises(DataSpecificationInvalidCommandException):
            self.dsg.break_loop()

        self.dsg.start_loop(0, 0, 0, True, True, True)
        self.dsg.break_loop()

        self.skip_words(2)
        # BREAK_LOOP
        self.assertEqual(self.get_next_word(), 0x05200000)

    def test_call_function(self):
        self.dsg.start_function(0, [])
        self.dsg.end_function()

        self.dsg.start_function(1, [True, True, False])
        self.dsg.end_function()

        self.dsg.define_structure(0, [("test", DataType.U08, 0)])
        self.dsg.define_structure(1, [("test", DataType.U08, 0)])
        self.dsg.define_structure(2, [("test", DataType.U08, 0)])

        self.dsg.call_function(0, [])
        self.dsg.call_function(1, [0, 1, 2])

        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.call_function(2, [])
        with self.assertRaises(DataSpecificationWrongParameterNumberException):
            self.dsg.call_function(1, [])
        with self.assertRaises(DataSpecificationWrongParameterNumberException):
            self.dsg.call_function(1, [0, 1])
        with self.assertRaises(DataSpecificationWrongParameterNumberException):
            self.dsg.call_function(1, [0, 1, 2, 3])
        with self.assertRaises(DataSpecificationDuplicateParameterException):
            self.dsg.call_function(1, [1, 1, 2])
        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.call_function(1, [1, 2, 3])
        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.call_function(1, [3, 2, 1])
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.call_function(-1, [0, 1, 2])
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.call_function(constants.MAX_CONSTRUCTORS, [0, 1])
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.call_function(1, [0, -1, 2])
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.call_function(1, [-1,  1, 2])
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.call_function(1, [0, 2, constants.MAX_STRUCT_SLOTS])

        self.skip_words(16)
        # CONSTRUCT
        self.assertEqual(self.get_next_word(), 0x04000000)
        self.assertEqual(self.get_next_word(), 0x14000100)
        self.assertEqual(self.get_next_word(), 0x00002040)

    def test_start_function(self):
        self.dsg.start_function(0, [])
        self.dsg.no_operation()
        self.dsg.end_function()

        self.dsg.start_function(1, [True, True, False])
        self.dsg.no_operation()
        self.dsg.end_function()

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.start_function(-1, [True])
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.start_function(constants.MAX_CONSTRUCTORS, [True])
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.start_function(2, [True, True, True, True, True, True])
        with self.assertRaises(DataSpecificationFunctionInUse):
            self.dsg.start_function(0, [])

        self.dsg.start_function(2, [False])

        with self.assertRaises(DataSpecificationInvalidCommandException):
            self.dsg.start_function(3, [])

        self.dsg.end_function()

        # START_CONSTRUCTOR
        self.assertEqual(self.get_next_word(), 0x02000000)
        self.skip_words(2)
        self.assertEqual(self.get_next_word(), 0x02000B03)
        self.skip_words(2)

    def test_end_function(self):
        with self.assertRaises(DataSpecificationInvalidCommandException):
            self.dsg.end_function()

        self.dsg.start_function(0, [])
        self.dsg.end_function()

        self.skip_words(1)
        # END_CONSTRUCTOR
        self.assertEqual(self.get_next_word(), 0x02500000)

    def test_logical_and(self):
        self.dsg.logical_and(0, 0x12, 0x34, False, False)
        self.dsg.logical_and(1, 0x12345678, 0xABCDEF14, False, False)

        self.dsg.logical_and(3, 2, 0xABCDEF14, True, False)
        self.dsg.logical_and(4, 0x12345678, 5, False, True)

        self.dsg.logical_and(4, 3, 5, True, True)
        self.dsg.logical_and(3, 3, 3, True, True)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_and(-1, 0x12, 0x34, False, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_and(constants.MAX_REGISTERS, 0x12, 0x34,
                                 False, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_and(1, -1, 0x34, True, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_and(1, constants.MAX_REGISTERS, 0x34,
                                 True, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_and(1, 0x12, -1, False, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_and(1, 0x34, constants.MAX_REGISTERS,
                                 False, True)

        # Logical AND
        self.assertEqual(self.get_next_word(3),
                         [0x26840003, 0x00000012, 0x00000034])
        self.assertEqual(self.get_next_word(3),
                         [0x26841003, 0x12345678, 0xABCDEF14])
        self.assertEqual(self.get_next_word(2), [0x16863203, 0xABCDEF14])
        self.assertEqual(self.get_next_word(2), [0x16854053, 0x12345678])
        self.assertEqual(self.get_next_word(), 0x06874353)
        self.assertEqual(self.get_next_word(), 0x06873333)

    def test_logical_or(self):
        self.dsg.logical_or(0, 0x12, 0x34, False, False)
        self.dsg.logical_or(1, 0x12345678, 0xABCDEF14, False, False)

        self.dsg.logical_or(3, 2, 0xABCDEF14, True, False)
        self.dsg.logical_or(4, 0x12345678, 5, False, True)

        self.dsg.logical_or(4, 3, 5, True, True)
        self.dsg.logical_or(3, 3, 3, True, True)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_or(-1, 0x12, 0x34, False, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_or(constants.MAX_REGISTERS, 0x12, 0x34,
                                False, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_or(1, -1, 0x34, True, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_or(1, constants.MAX_REGISTERS, 0x34,
                                True, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_or(1, 0x12, -1, False, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_or(1, 0x34, constants.MAX_REGISTERS,
                                False, True)

        # Logical OR
        self.assertEqual(self.get_next_word(3),
                         [0x26840002, 0x00000012, 0x00000034])
        self.assertEqual(self.get_next_word(3),
                         [0x26841002, 0x12345678, 0xABCDEF14])
        self.assertEqual(self.get_next_word(2), [0x16863202, 0xABCDEF14])
        self.assertEqual(self.get_next_word(2), [0x16854052, 0x12345678])
        self.assertEqual(self.get_next_word(), 0x06874352)
        self.assertEqual(self.get_next_word(), 0x06873332)

    def test_logical_xor(self):
        self.dsg.logical_xor(0, 0x12, 0x34, False, False)
        self.dsg.logical_xor(1, 0x12345678, 0xABCDEF14, False, False)

        self.dsg.logical_xor(3, 2, 0xABCDEF14, True, False)
        self.dsg.logical_xor(4, 0x12345678, 5, False, True)

        self.dsg.logical_xor(4, 3, 5, True, True)
        self.dsg.logical_xor(3, 3, 3, True, True)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_xor(-1, 0x12, 0x34, False, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_xor(constants.MAX_REGISTERS, 0x12, 0x34,
                                 False, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_xor(1, -1, 0x34, True, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_xor(1, constants.MAX_REGISTERS, 0x34,
                                 True, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_xor(1, 0x12, -1, False, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_xor(1, 0x34, constants.MAX_REGISTERS,
                                 False, True)

        # Logical XOR
        self.assertEqual(self.get_next_word(3),
                         [0x26840004, 0x00000012, 0x00000034])
        self.assertEqual(self.get_next_word(3),
                         [0x26841004, 0x12345678, 0xABCDEF14])
        self.assertEqual(self.get_next_word(2), [0x16863204, 0xABCDEF14])
        self.assertEqual(self.get_next_word(2), [0x16854054, 0x12345678])
        self.assertEqual(self.get_next_word(), 0x06874354)
        self.assertEqual(self.get_next_word(), 0x06873334)

    def test_logical_left_shift(self):
        self.dsg.logical_left_shift(0, 0x12, 0x34, False, False)
        self.dsg.logical_left_shift(1, 0x12345678, 0xABCDEF14, False, False)

        self.dsg.logical_left_shift(3, 2, 0xABCDEF14, True, False)
        self.dsg.logical_left_shift(4, 0x12345678, 5, False, True)

        self.dsg.logical_left_shift(4, 3, 5, True, True)
        self.dsg.logical_left_shift(3, 3, 3, True, True)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_left_shift(-1, 0x12, 0x34, False, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_left_shift(constants.MAX_REGISTERS, 0x12, 0x34,
                                        False, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_left_shift(1, -1, 0x34, True, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_left_shift(1, constants.MAX_REGISTERS, 0x34,
                                        True, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_left_shift(1, 0x12, -1, False, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_left_shift(1, 0x34, constants.MAX_REGISTERS,
                                        False, True)

        # Logical LEFT_SHIFT
        self.assertEqual(self.get_next_word(3),
                         [0x26840000, 0x00000012, 0x00000034])
        self.assertEqual(self.get_next_word(3),
                         [0x26841000, 0x12345678, 0xABCDEF14])
        self.assertEqual(self.get_next_word(2), [0x16863200, 0xABCDEF14])
        self.assertEqual(self.get_next_word(2), [0x16854050, 0x12345678])
        self.assertEqual(self.get_next_word(), 0x06874350)
        self.assertEqual(self.get_next_word(), 0x06873330)

    def test_logical_not(self):
        self.dsg.logical_not(1, 0x12345678, False)

        self.dsg.logical_not(3, 2, True)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_not(-1, 0x12, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_not(constants.MAX_REGISTERS, 0x12, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_not(1, -1, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_not(1, constants.MAX_REGISTERS, True)

        # Logical NOT
        self.assertEqual(self.get_next_word(2), [0x16841005, 0x12345678])
        self.assertEqual(self.get_next_word(), 0x06863205)

    def test_logical_right_shift(self):
        self.dsg.logical_right_shift(0, 0x12, 0x34, False, False)
        self.dsg.logical_right_shift(1, 0x12345678, 0xABCDEF14, False, False)

        self.dsg.logical_right_shift(3, 2, 0xABCDEF14, True, False)
        self.dsg.logical_right_shift(4, 0x12345678, 5, False, True)

        self.dsg.logical_right_shift(4, 3, 5, True, True)
        self.dsg.logical_right_shift(3, 3, 3, True, True)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_right_shift(-1, 0x12, 0x34, False, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_right_shift(constants.MAX_REGISTERS, 0x12, 0x34,
                                         False, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_right_shift(1, -1, 0x34, True, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_right_shift(1, constants.MAX_REGISTERS, 0x34,
                                         True, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_right_shift(1, 0x12, -1, False, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.logical_right_shift(1, 0x34, constants.MAX_REGISTERS,
                                         False, True)

        # Logical RIGHT_SHIFT
        self.assertEqual(self.get_next_word(3),
                         [0x26840001, 0x00000012, 0x00000034])
        self.assertEqual(self.get_next_word(3),
                         [0x26841001, 0x12345678, 0xABCDEF14])
        self.assertEqual(self.get_next_word(2), [0x16863201, 0xABCDEF14])
        self.assertEqual(self.get_next_word(2), [0x16854051, 0x12345678])
        self.assertEqual(self.get_next_word(), 0x06874351)
        self.assertEqual(self.get_next_word(), 0x06873331)

    def test_comment(self):
        self.dsg.comment("test")

        # Comment generated data specification
        self.assertEqual(self.spec_writer.tell(), 0)
        self.assertEqual(self.report_writer.getvalue(), "test\n")

    def test_copy_structure(self):
        self.dsg.define_structure(0, [("first", DataType.UINT8, 0xAB)])
        self.dsg.define_structure(1, [("first", DataType.UINT8, 0xAB),
                                      ("second", DataType.UINT32, 0x12345679),
                                      ("third", DataType.INT16, None)])

        self.dsg.copy_structure(0, 2, False, False)
        self.dsg.copy_structure(1, 3, False, False)
        self.dsg.copy_structure(1, 4, True, False)
        self.dsg.copy_structure(0, 3, False, True)
        self.dsg.copy_structure(3, 4, True, True)

        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.copy_structure(2, 3)
        with self.assertRaises(DataSpecificationDuplicateParameterException):
            self.dsg.copy_structure(2, 2)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure(-1, 2, True, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure(constants.MAX_REGISTERS, 2, True, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure(1, -1, False, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure(1, constants.MAX_REGISTERS, False, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure(-1, 2, False, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure(constants.MAX_STRUCT_SLOTS, 2, False,
                                    False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure(1, -1, False, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure(1, constants.MAX_STRUCT_SLOTS, False, True)

        self.skip_words(11)
        # COPY_STRUCT
        self.assertEqual(self.get_next_word(), 0x07002000)
        self.assertEqual(self.get_next_word(), 0x07003100)
        self.assertEqual(self.get_next_word(), 0x07024100)
        self.assertEqual(self.get_next_word(), 0x07043000)
        self.assertEqual(self.get_next_word(), 0x07064300)

    def test_copy_structure_parameter(self):
        self.dsg.define_structure(0, [("first", DataType.UINT8, 0xAB),
                                      ("second", DataType.INT16, 0xBC)])
        self.dsg.define_structure(1, [("first", DataType.UINT8, 0xAB),
                                      ("second", DataType.UINT32, 0x12345679),
                                      ("third", DataType.INT16, None)])

        self.dsg.copy_structure_parameter(0, 0, 1, 0, False)
        self.dsg.copy_structure_parameter(0, 0, 0, 0, True)
        self.dsg.copy_structure_parameter(0, 1, 1, 2, False)
        self.dsg.copy_structure_parameter(0, 1, 2,
                                          destination_is_register=True)
        self.dsg.copy_structure_parameter(1, 0, 3,
                                          destination_is_register=True)
        self.dsg.copy_structure_parameter(1, 2, 2, -1,
                                          destination_is_register=True)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure_parameter(-1, 0, 1, 0, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure_parameter(constants.MAX_STRUCT_SLOTS, 0, 1,
                                              0, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure_parameter(0, 0, -1, 0, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure_parameter(0, 0, constants.MAX_STRUCT_SLOTS,
                                              0, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure_parameter(0, 0, -1, 0, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure_parameter(0, 0, constants.MAX_REGISTERS, 0,
                                              True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure_parameter(0, -1, 1, 0, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure_parameter(0, constants.MAX_STRUCT_ELEMENTS,
                                              1, 0, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure_parameter(0, 0, 1, -1, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure_parameter(0, 0, 1,
                                              constants.MAX_STRUCT_ELEMENTS,
                                              False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure_parameter(0, 0, -1, 0, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.copy_structure_parameter(0, 0, constants.MAX_REGISTERS, 0,
                                              True)
        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.copy_structure_parameter(2, 0, 0, 0, False)
        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.copy_structure_parameter(0, 0, 2, 0, False)
        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.copy_structure_parameter(0, 4, 1, 0, False)
        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.copy_structure_parameter(0, 0, 1, 4, False)
        with self.assertRaises(DataSpecificationDuplicateParameterException):
            self.dsg.copy_structure_parameter(0, 0, 0, 0, False)
        with self.assertRaises(DataSpecificationTypeMismatchException):
            self.dsg.copy_structure_parameter(0, 0, 1, 1, False)

        self.skip_words(13)
        # COPY_PARAM
        self.assertEqual(self.get_next_word(2), [0x17101000, 0x00000000])
        self.assertEqual(self.get_next_word(2), [0x17140000, 0x00000000])
        self.assertEqual(self.get_next_word(2), [0x17101000, 0x00000201])
        self.assertEqual(self.get_next_word(2), [0x17142000, 0x00000001])
        self.assertEqual(self.get_next_word(2), [0x17143100, 0x00000000])
        self.assertEqual(self.get_next_word(2), [0x17142100, 0x00000002])

    def test_start_loop(self):
        self.dsg.start_loop(0, 1, 2)
        self.dsg.start_loop(2, 0x02345678, 0x0ABBCCDD)
        self.dsg.start_loop(0, 1, 2, 5)
        self.dsg.start_loop(1, 0x02345678, 0x0ABBCCDD, 0x01111111)
        self.dsg.start_loop(0, 10, 2, -1)
        self.dsg.start_loop(1, 2, 3, 4, True, False, False)
        self.dsg.start_loop(1, 5, 3, 4, False, True, False)
        self.dsg.start_loop(2, 2, 3, 5, False, False, True)
        self.dsg.start_loop(1, 2, 3, 4, True, True, True)
        self.dsg.start_loop(5, 1, 1, 1, False, False, False)
        self.dsg.start_loop(1, 1, 1, 1, True, True, True)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.start_loop(-1, 0, 1)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.start_loop(constants.MAX_REGISTERS, 0, 1)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.start_loop(1, -1, 1, 1, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.start_loop(1, constants.MAX_REGISTERS, 0, 1, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.start_loop(1, 1, -1, 1, False, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.start_loop(1, 1, constants.MAX_REGISTERS, 1, False, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.start_loop(1, 1, 1, -1, False, False, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.start_loop(1, 1, 1, constants.MAX_REGISTERS, False, False,
                                True)

        # LOOP
        self.assertEqual(self.get_next_word(4), [0x35100000, 1, 2, 1])
        self.assertEqual(self.get_next_word(4),
                         [0x35100002, 0x02345678, 0x0ABBCCDD, 0x00000001])
        self.assertEqual(self.get_next_word(4), [0x35100000, 1, 2, 5])
        self.assertEqual(self.get_next_word(4),
                         [0x35100001, 0x02345678, 0x0ABBCCDD, 0x01111111])
        self.assertEqual(self.get_next_word(4),
                         [0x35100000, 0x0000000A, 0x00000002, 0xFFFFFFFF])
        self.assertEqual(self.get_next_word(3),
                         [0x25142001, 0x00000003, 0x00000004])
        self.assertEqual(self.get_next_word(3),
                         [0x25120301, 0x00000005, 0x00000004])
        self.assertEqual(self.get_next_word(3),
                         [0x25110052, 0x00000002, 0x00000003])
        self.assertEqual(self.get_next_word(), 0x05172341)
        self.assertEqual(self.get_next_word(4), [0x35100005, 1, 1, 1])
        self.assertEqual(self.get_next_word(), 0x05171111)

    def test_end_loop(self):
        self.dsg.end_loop()
        # END_LOOP
        self.assertEqual(self.get_next_word(), 0x05300000)

    def test_start_conditional(self):
        self.dsg.start_conditional(0, Condition.EQUAL, 0, False)
        self.dsg.start_conditional(2, Condition.EQUAL, 1, False)
        self.dsg.start_conditional(3, Condition.NOT_EQUAL, 1, False)
        self.dsg.start_conditional(4, Condition.LESS_THAN_OR_EQUAL, 3, False)
        self.dsg.start_conditional(4, Condition.LESS_THAN, 3, False)
        self.dsg.start_conditional(4, Condition.GREATER_THAN_OR_EQUAL, 5,
                                   False)
        self.dsg.start_conditional(2, Condition.GREATER_THAN, 5, False)

        self.dsg.start_conditional(0, Condition.EQUAL, 1, True)
        self.dsg.start_conditional(4, Condition.LESS_THAN, 3, True)
        self.dsg.start_conditional(2, Condition.GREATER_THAN, 5, True)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.start_conditional(-1, Condition.EQUAL, 0, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.start_conditional(constants.MAX_REGISTERS,
                                       Condition.EQUAL, 0, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.start_conditional(0, Condition.EQUAL, -1, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.start_conditional(0, Condition.EQUAL,
                                       constants.MAX_REGISTERS, True)

        # IF
        self.assertEqual(self.get_next_word(2), [0x15520000, 0x00000000])
        self.assertEqual(self.get_next_word(2), [0x15520200, 0x00000001])
        self.assertEqual(self.get_next_word(2), [0x15520301, 0x00000001])
        self.assertEqual(self.get_next_word(2), [0x15520402, 0x00000003])
        self.assertEqual(self.get_next_word(2), [0x15520403, 0x00000003])
        self.assertEqual(self.get_next_word(2), [0x15520404, 0x00000005])
        self.assertEqual(self.get_next_word(2), [0x15520205, 0x00000005])
        self.assertEqual(self.get_next_word(), 0x05530010)
        self.assertEqual(self.get_next_word(), 0x05530433)
        self.assertEqual(self.get_next_word(), 0x05530255)

    def test_else_conditional(self):
        with self.assertRaises(DataSpecificationInvalidCommandException):
            self.dsg.else_conditional()

        self.dsg.start_conditional(0, Condition.EQUAL, 0, True)
        self.dsg.else_conditional()

        with self.assertRaises(DataSpecificationInvalidCommandException):
            self.dsg.else_conditional()

        self.dsg.start_conditional(0, Condition.EQUAL, 0, False)
        self.dsg.else_conditional()

        with self.assertRaises(DataSpecificationInvalidCommandException):
            self.dsg.else_conditional()

        self.skip_words(1)
        # ELSE
        self.assertEqual(self.get_next_word(), 0x05600000)
        self.skip_words(2)
        self.assertEqual(self.get_next_word(), 0x05600000)

    def test_end_conditional(self):
        with self.assertRaises(DataSpecificationInvalidCommandException):
            self.dsg.end_conditional()

        self.dsg.start_conditional(0, Condition.EQUAL, 0, True)
        self.dsg.end_conditional()

        with self.assertRaises(DataSpecificationInvalidCommandException):
            self.dsg.end_conditional()

        self.dsg.start_conditional(0, Condition.EQUAL, 0, False)
        self.dsg.else_conditional()
        self.dsg.end_conditional()

        with self.assertRaises(DataSpecificationInvalidCommandException):
            self.dsg.end_conditional()

        self.skip_words(1)
        # END_IF
        self.assertEqual(self.get_next_word(), 0x05700000)
        self.skip_words(3)
        self.assertEqual(self.get_next_word(), 0x05700000)

    def test_switch_write_focus(self):
        self.dsg.reserve_memory_region(0, 100)
        self.dsg.reserve_memory_region(2, 100)
        self.dsg.reserve_memory_region(1, 100, empty=True)

        self.dsg.switch_write_focus(0)
        self.dsg.switch_write_focus(2)

        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.switch_write_focus(3)
        with self.assertRaises(DataSpecificationRegionUnfilledException):
            self.dsg.switch_write_focus(1)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.switch_write_focus(-1)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.switch_write_focus(constants.MAX_MEM_REGIONS)

        self.skip_words(6)
        # SWITCH_FOCUS
        self.assertEqual(self.get_next_word(), 0x05000000)
        self.assertEqual(self.get_next_word(), 0x05000200)

    def test_save_write_pointer(self):
        with self.assertRaises(DataSpecificationNoRegionSelectedException):
            self.dsg.save_write_pointer(0)

        self.dsg.reserve_memory_region(0, 100)

        with self.assertRaises(DataSpecificationNoRegionSelectedException):
            self.dsg.save_write_pointer(0)

        self.dsg.switch_write_focus(0)
        self.dsg.save_write_pointer(0)
        self.dsg.save_write_pointer(5)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.save_write_pointer(-1)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.save_write_pointer(constants.MAX_REGISTERS)

        self.skip_words(3)
        # GET_WR_PTR
        self.assertEqual(self.get_next_word(), 0x06340000)
        self.assertEqual(self.get_next_word(), 0x06345000)

    def test_print_struct(self):
        self.dsg.define_structure(0, [("first", DataType.UINT8, 0xAB)])
        self.dsg.define_structure(1, [("first", DataType.UINT8, 0xAB),
                                      ("second", DataType.UINT32, 0x12345679),
                                      ("third", DataType.INT16, None)])

        self.dsg.print_struct(0)
        self.dsg.print_struct(1)
        self.dsg.print_struct(2, True)
        self.dsg.print_struct(3, True)

        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.print_struct(2)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.print_struct(-1)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.print_struct(-1, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.print_struct(constants.MAX_STRUCT_SLOTS)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.print_struct(constants.MAX_REGISTERS, True)

        self.skip_words(11)
        # PRINT_STRUCT
        self.assertEqual(self.get_next_word(), 0x08200000)
        self.assertEqual(self.get_next_word(), 0x08200001)
        self.assertEqual(self.get_next_word(), 0x08220200)
        self.assertEqual(self.get_next_word(), 0x08220300)

    def test_print_text(self):
        self.dsg.print_text("t")
        self.dsg.print_text("te")
        self.dsg.print_text("test")
        self.dsg.print_text("test1234")
        self.dsg.print_text("test12345678")

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.print_text("test123456789")

        # PRINT_TEXT
        self.assertEqual(self.get_next_word(2), [0x18100000, 0x00000074])
        self.assertEqual(self.get_next_word(2), [0x18100001, 0x00006574])
        self.assertEqual(self.get_next_word(2), [0x18100003, 0x74736574])
        self.assertEqual(self.get_next_word(3),
                         [0x28100007, 0x74736574, 0x34333231])
        self.assertEqual(self.get_next_word(4),
                         [0x3810000B, 0x74736574, 0x34333231, 0x38373635])

    def test_print_value(self):
        self.dsg.print_value(0x78, False, DataType.UINT8)
        self.dsg.print_value(0x12345678)
        self.dsg.print_value(0, True)
        self.dsg.print_value(2, True)
        self.dsg.print_value(2, True, DataType.INT32)
        self.dsg.print_value(2, True, DataType.INT64)
        self.dsg.print_value(0x123456789ABCDEF, False, DataType.UINT64)
        self.dsg.print_value(2, True, DataType.U88)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.print_value(0x123456789)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.print_value(-1, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.print_value(constants.MAX_REGISTERS, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.print_value(0x12345678, False, DataType.INT16)

        # PRINT_VAL
        self.assertEqual(self.get_next_word(2), [0x18000000, 0x00000078])
        self.assertEqual(self.get_next_word(2), [0x18000002, 0x12345678])
        self.assertEqual(self.get_next_word(), 0x08020002)
        self.assertEqual(self.get_next_word(), 0x08020202)
        self.assertEqual(self.get_next_word(), 0x08020206)
        self.assertEqual(self.get_next_word(), 0x08020207)
        self.assertEqual(self.get_next_word(3),
                         [0x28000003, 0x89ABCDEF, 0x01234567])

    def test_set_register_value(self):
        self.dsg.set_register_value(0, 0, False, DataType.UINT32)
        self.dsg.set_register_value(1, 0x12345678, False, DataType.UINT32)
        self.dsg.set_register_value(2, 0x123456789ABCDEF, False,
                                    DataType.UINT64)
        self.dsg.set_register_value(2, 0x01234567, False, DataType.INT32)
        self.dsg.set_register_value(3, 0x67, False, DataType.UINT8)

        self.dsg.set_register_value(3, 2, True, DataType.UINT64)
        self.dsg.set_register_value(3, 2, True, DataType.U88)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.set_register_value(-1, 0)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.set_register_value(constants.MAX_REGISTERS, 0)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.set_register_value(0, -1, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.set_register_value(0, constants.MAX_REGISTERS, True)
        with self.assertRaises(DataSpecificationDuplicateParameterException):
            self.dsg.set_register_value(0, 0, True)

        # MV
        self.assertEqual(self.get_next_word(2), [0x16040000, 0x00000000])
        self.assertEqual(self.get_next_word(2), [0x16041000, 0x12345678])
        self.assertEqual(self.get_next_word(3),
                         [0x26042000, 0x89ABCDEF, 0x01234567])
        self.assertEqual(self.get_next_word(2), [0x16042000, 0x01234567])
        self.assertEqual(self.get_next_word(2), [0x16043000, 0x00000067])
        self.assertEqual(self.get_next_word(), 0x06063200)
        self.assertEqual(self.get_next_word(), 0x06063200)

    def test_set_write_pointer(self):
        with self.assertRaises(DataSpecificationNoRegionSelectedException):
            self.dsg.set_write_pointer(0x100)

        # Define a memory region and switch focus to it
        self.dsg.reserve_memory_region(1, 100)
        self.dsg.switch_write_focus(1)

        self.dsg.set_write_pointer(0x12345678, False, False)
        self.dsg.set_write_pointer(0x00000078, False, False)
        self.dsg.set_write_pointer(0x12, False, True)
        self.dsg.set_write_pointer(-12, False, True)
        self.dsg.set_write_pointer(1, True, True)
        self.dsg.set_write_pointer(3, True, False)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.set_write_pointer(-1, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.set_write_pointer(constants.MAX_REGISTERS, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.set_write_pointer(0x123456789, False)

        self.skip_words(3)
        # SET_WR_PTR
        self.assertEqual(self.get_next_word(2), [0x16400000, 0x12345678])
        self.assertEqual(self.get_next_word(2), [0x16400000, 0x00000078])
        self.assertEqual(self.get_next_word(2), [0x16400001, 0x00000012])
        self.assertEqual(self.get_next_word(2), [0x16400001, 0xFFFFFFF4])
        self.assertEqual(self.get_next_word(), 0x06420101)
        self.assertEqual(self.get_next_word(), 0x06420300)

    def test_write_value(self):
        with self.assertRaises(DataSpecificationNoRegionSelectedException):
            self.dsg.write_value(0x0)

        self.dsg.reserve_memory_region(0, 100)
        self.dsg.switch_write_focus(0)

        self.dsg.write_value(0x0)
        self.dsg.write_value(0x12)
        self.dsg.write_value(0x12345678)
        self.dsg.write_value(0x12345678, 2)
        self.dsg.write_value(0x12, 12)
        self.dsg.write_value(0x12, 0xFF, False, DataType.UINT8)
        self.dsg.write_value(0x12, 5, False, DataType.UINT16)
        self.dsg.write_value(0x123456789ABCDEF, 5, False, DataType.UINT64)
        self.dsg.write_value(0x123456789ABCDEF, 5, True, DataType.UINT64)
        self.dsg.write_value(0x123, 2, True, DataType.UINT64)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_value(0, -1, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_value(0, 0, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_value(0, constants.MAX_REGISTERS, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_value(0, -1, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_value(0, 256, False)

        self.skip_words(3)
        # WRITE
        self.assertEqual(self.get_next_word(2), [0x14202001, 0x00000000])
        self.assertEqual(self.get_next_word(2), [0x14202001, 0x00000012])
        self.assertEqual(self.get_next_word(2), [0x14202001, 0x12345678])
        self.assertEqual(self.get_next_word(2), [0x14202002, 0x12345678])
        self.assertEqual(self.get_next_word(2), [0x1420200C, 0x00000012])
        self.assertEqual(self.get_next_word(2), [0x142000FF, 0x00000012])
        self.assertEqual(self.get_next_word(2), [0x14201005, 0x00000012])
        self.assertEqual(self.get_next_word(3),
                         [0x24203005, 0x89ABCDEF, 0x01234567])
        self.assertEqual(self.get_next_word(3),
                         [0x24213050, 0x89ABCDEF, 0x01234567])
        self.assertEqual(self.get_next_word(3),
                         [0x24213020, 0x00000123, 0x00000000])

    def test_write_structure(self):
        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.write_structure(0)

        self.dsg.define_structure(0, [("first", DataType.UINT8, 0xAB)])
        self.dsg.define_structure(1, [("first", DataType.UINT8, 0xAB),
                                      ("second", DataType.UINT32, 0x12345679),
                                      ("third", DataType.INT16, None)])
        self.dsg.define_structure(0xA, [("first", DataType.UINT8, 0xAB)])

        self.dsg.write_structure(0)
        self.dsg.write_structure(0, 2)
        self.dsg.write_structure(0, 5, True)
        self.dsg.write_structure(1, 5, True)
        self.dsg.write_structure(0xA, 0xF)
        self.dsg.write_structure(0xA, 0xF, True)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_structure(-1)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_structure(constants.MAX_STRUCT_SLOTS)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_structure(1, -1, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_structure(1, constants.MAX_STRUCT_SLOTS, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_structure(-1)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_structure(16)

        self.skip_words(15)
        # WRITE_STRUCT
        self.assertEqual(self.get_next_word(), 0x04400100)
        self.assertEqual(self.get_next_word(), 0x04400200)
        self.assertEqual(self.get_next_word(), 0x04420500)
        self.assertEqual(self.get_next_word(), 0x04420501)
        self.assertEqual(self.get_next_word(), 0x04400F0A)
        self.assertEqual(self.get_next_word(), 0x04420F0A)

    def test_write_array_working_subset(self):
        with self.assertRaises(DataSpecificationNoRegionSelectedException):
            self.dsg.write_array([0, 1, 2, 3], DataType.UINT32)

        self.dsg.reserve_memory_region(0, 100)
        self.dsg.switch_write_focus(0)

        self.dsg.write_array([], DataType.UINT32)
        self.dsg.write_array([0, 1, 2, 3], DataType.UINT32)

        self.skip_words(3)
        # WRITE_ARRAY
        self.assertEqual(self.get_next_word(2), [0x14300004, 0])
        self.assertEqual(self.get_next_word(6), [0x14300004, 4, 0, 1, 2, 3])

    @unittest.skip("buggy")
    def test_write_array(self):
        # TODO: Make write_array work with non-UINT32
        with self.assertRaises(DataSpecificationNoRegionSelectedException):
            self.dsg.write_array([0, 1, 2, 3], DataType.UINT8)

        self.dsg.reserve_memory_region(0, 100)
        self.dsg.switch_write_focus(0)

        self.dsg.write_array([], DataType.UINT8)
        self.dsg.write_array([0, 1, 2, 3], DataType.UINT8)
        self.dsg.write_array([0, 1, 2, 3], DataType.UINT16)
        self.dsg.write_array([0, 1, 2, 3], DataType.UINT32)
        self.dsg.write_array([0, 1, 2, 3, 4], DataType.UINT16)
        self.dsg.write_array([0, 1, 2, 3, 4], DataType.UINT8)

        self.skip_words(3)
        # WRITE_ARRAY
        self.assertEqual(self.get_next_word(2), [0x14300001, 0])
        self.assertEqual(self.get_next_word(3), [0x14300001, 4, 0x03020100])
        self.assertEqual(self.get_next_word(4),
                         [0x14300002, 4, 0x00010000, 0x00030002])
        self.assertEqual(self.get_next_word(6), [0x14300004, 4, 0, 1, 2, 3])
        self.assertEqual(self.get_next_word(5),
                         [0x14300002, 5, 0x00010000, 0x00030002, 0x00000004])
        self.assertEqual(self.get_next_word(4),
                         [0x14300001, 5, 0x03020100, 0x00000004])

    def test_set_structure_value(self):
        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.set_structure_value(0, 0, 0, DataType.UINT32)

        self.dsg.define_structure(0, [("first", DataType.UINT8, 0xAB)])
        self.dsg.define_structure(1, [("first", DataType.UINT8, 0xAB),
                                      ("second", DataType.UINT32, 0x12345679),
                                      ("third", DataType.INT16, None)])
        self.dsg.define_structure(0xA, [("first", DataType.UINT8, 0xAB),
                                        ("second", DataType.UINT64, None)])

        self.dsg.set_structure_value(0, 0, 0x12, DataType.UINT8)
        self.dsg.set_structure_value(1, 2, 0x1234, DataType.INT16)
        self.dsg.set_structure_value(1, 1, 0x12345678, DataType.UINT32)
        self.dsg.set_structure_value(10, 1, 0x123456789ABCDEF,
                                     DataType.UINT64)

        self.dsg.set_structure_value(1, 0, 2, DataType.UINT8, True)
        self.dsg.set_structure_value(1, 1, 3, DataType.UINT32, True)
        self.dsg.set_structure_value(10, 1, 5, DataType.UINT64, True)

        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.set_structure_value(0, 1, 0, DataType.UINT8)
        with self.assertRaises(DataSpecificationTypeMismatchException):
            self.dsg.set_structure_value(0, 0, 0, DataType.UINT16)
        with self.assertRaises(DataSpecificationTypeMismatchException):
            self.dsg.set_structure_value(1, 1, 0, DataType.UINT8)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.set_structure_value(-1, 0, 0, DataType.UINT32)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.set_structure_value(constants.MAX_STRUCT_SLOTS, 0, 0,
                                         DataType.UINT32)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.set_structure_value(0, -1, 0, DataType.UINT32)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.set_structure_value(0, constants.MAX_STRUCT_ELEMENTS, 0,
                                         DataType.UINT32)

        self.skip_words(16)
        # WRITE_PARAM
        self.assertEqual(self.get_next_word(2), [0x17200000, 0x00000012])
        self.assertEqual(self.get_next_word(2), [0x17201002, 0x00001234])
        self.assertEqual(self.get_next_word(2), [0x17201001, 0x12345678])
        self.assertEqual(self.get_next_word(3),
                         [0x2720A001, 0x89ABCDEF, 0x01234567])
        self.assertEqual(self.get_next_word(), 0x07221200)
        self.assertEqual(self.get_next_word(), 0x07221301)
        self.assertEqual(self.get_next_word(), 0x0722A501)

    def test_end_specification(self):
        self.dsg.end_specification(False)

        # END_SPEC
        self.assertEqual(self.get_next_word(), 0x0FF00000)

        self.dsg.end_specification()
        with self.assertRaises(ValueError):
            self.get_next_word()

    def test_declare_random_number_generator(self):
        self.dsg.declare_random_number_generator(
            0, RandomNumberGenerator.MERSENNE_TWISTER, 0x12345678)
        self.dsg.declare_random_number_generator(
            3, RandomNumberGenerator.MERSENNE_TWISTER, 0x12)

        with self.assertRaises(DataSpecificationRNGInUseException):
            self.dsg.declare_random_number_generator(
                0, RandomNumberGenerator.MERSENNE_TWISTER, 0x12345678)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.declare_random_number_generator(
                -1, RandomNumberGenerator.MERSENNE_TWISTER, 0x12345678)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.declare_random_number_generator(
                constants.MAX_RANDOM_DISTS,
                RandomNumberGenerator.MERSENNE_TWISTER, 0x12345678)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.declare_random_number_generator(
                1, RandomNumberGenerator.MERSENNE_TWISTER, 0x123456789)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.declare_random_number_generator(
                2, RandomNumberGenerator.MERSENNE_TWISTER, -1)

        # DECLARE_RNG
        self.assertEqual(self.get_next_word(2), [0x10500000, 0x12345678])
        self.assertEqual(self.get_next_word(2), [0x10503000, 0x00000012])

    def test_declare_uniform_random_distribution(self):
        self.dsg.declare_random_number_generator(
            3, RandomNumberGenerator.MERSENNE_TWISTER, 0x12345678)

        self.dsg.declare_uniform_random_distribution(0, 0, 3, 10, 100)
        self.dsg.declare_uniform_random_distribution(2, 4, 3, 50, 200)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.declare_uniform_random_distribution(-1, 2, 3, 10, 100)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.declare_uniform_random_distribution(
                constants.MAX_RANDOM_DISTS, 2, 3, 10, 100)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.declare_uniform_random_distribution(1, -1, 3, 10, 100)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.declare_uniform_random_distribution(
                1, constants.MAX_STRUCT_SLOTS, 3, 10, 100)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.declare_uniform_random_distribution(1, 1, -1, 10, 100)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.declare_uniform_random_distribution(
                1, 1, constants.MAX_RNGS, 10, 100)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.declare_uniform_random_distribution(
                1, 4, 3,  DataType.S1615.min - 1, 100)  # @UndefinedVariable
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.declare_uniform_random_distribution(
                1, 4, 3, 100, DataType.S1615.max + 1)  # @UndefinedVariable
        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.declare_uniform_random_distribution(1, 1, 1, 100, 200)
        with self.assertRaises(
                DataSpecificationRandomNumberDistributionInUseException):
            self.dsg.declare_uniform_random_distribution(0, 1, 3, 100, 200)

        # DECLARE_RNG
        self.assertEqual(self.get_next_word(2), [0x10503000, 0x12345678])
        # START_STRUCT
        self.assertEqual(self.get_next_word(), 0x01000000)
        # STRUCT_ELEM
        self.assertEqual(self.get_next_word(2), [0x11100002, 0x00000000])
        # STRUCT_ELEM
        self.assertEqual(self.get_next_word(2), [0x11100002, 0x00000003])
        # STRUCT_ELEM
        self.assertEqual(self.get_next_word(2), [0x1110000C, 0x00050000])
        # STRUCT_ELEM
        self.assertEqual(self.get_next_word(2), [0x1110000C, 0x00320000])
        # END_STRUCT
        self.assertEqual(self.get_next_word(), 0x01200000)
        # DECLARE_RANDOM_DIST
        self.assertEqual(self.get_next_word(), 0x00600000)
        # START_STRUCT
        self.assertEqual(self.get_next_word(), 0x01000004)
        # STRUCT_ELEM
        self.assertEqual(self.get_next_word(2), [0x11100002, 0x00000000])
        # STRUCT_ELEM
        self.assertEqual(self.get_next_word(2), [0x11100002, 0x00000003])
        # STRUCT_ELEM
        self.assertEqual(self.get_next_word(2), [0x1110000C, 0x00190000])
        # STRUCT_ELEM
        self.assertEqual(self.get_next_word(2), [0x1110000C, 0x00640000])
        # END_STRUCT
        self.assertEqual(self.get_next_word(), 0x01200000)
        # DECLARE_RANDOM_DIST
        self.assertEqual(self.get_next_word(), 0x00600204)

    def test_call_random_distribution(self):
        self.dsg.declare_random_number_generator(
            3, RandomNumberGenerator.MERSENNE_TWISTER, 0x12345678)

        self.dsg.declare_uniform_random_distribution(3, 0, 3, 10, 100)

        self.dsg.call_random_distribution(3, 1)
        self.dsg.call_random_distribution(3, 5)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.call_random_distribution(-1, 2)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.call_random_distribution(constants.MAX_RANDOM_DISTS, 2)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.call_random_distribution(3, -1)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.call_random_distribution(3, constants.MAX_REGISTERS)
        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.call_random_distribution(1, 1)

        self.skip_words(13)
        # GET_RANDOM_NUMBER
        self.assertEqual(self.get_next_word(), 0x00741003)
        self.assertEqual(self.get_next_word(), 0x00745003)

    def test_get_structure_value(self):
        self.dsg.define_structure(0, [("first", DataType.UINT8, 0xAB)])
        self.dsg.define_structure(1, [("first", DataType.UINT8, 0xAB),
                                      ("second", DataType.UINT32, 0x12345679),
                                      ("third", DataType.INT16, None),
                                      ("fourth", DataType.UINT64,
                                       0x123456789ABCDEF)])

        self.dsg.get_structure_value(0, 0, 0, False)
        self.dsg.get_structure_value(3, 0, 0, False)
        self.dsg.get_structure_value(2, 1, 1, False)
        self.dsg.get_structure_value(3, 1, 3, False)

        self.dsg.get_structure_value(3, 1, 3, True)
        self.dsg.get_structure_value(3, 0, 0, True)
        self.dsg.get_structure_value(3, 0, 5, True)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.get_structure_value(-1, 0, 0, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.get_structure_value(constants.MAX_REGISTERS, 0, 0, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.get_structure_value(0, -1, 0, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.get_structure_value(0, constants.MAX_STRUCT_SLOTS, 0,
                                         False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.get_structure_value(0, 0, -1, False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.get_structure_value(0, 0, constants.MAX_STRUCT_ELEMENTS,
                                         False)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.get_structure_value(0, 0, -1, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.get_structure_value(0, 0, constants.MAX_REGISTERS, True)
        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.get_structure_value(0, 2, 0)
        with self.assertRaises(DataSpecificationNotAllocatedException):
            self.dsg.get_structure_value(0, 0, 1)

        self.skip_words(14)
        # READ_PARAM
        self.assertEqual(self.get_next_word(), 0x07340000)
        self.assertEqual(self.get_next_word(), 0x07343000)
        self.assertEqual(self.get_next_word(), 0x07342011)
        self.assertEqual(self.get_next_word(), 0x07343031)
        self.assertEqual(self.get_next_word(), 0x07363301)
        self.assertEqual(self.get_next_word(), 0x07363000)
        self.assertEqual(self.get_next_word(), 0x07363500)

    def test_read_value(self):
        self.dsg.read_value(0, DataType.UINT32)
        self.dsg.read_value(1, DataType.UINT64)
        self.dsg.read_value(2, DataType.INT32)
        self.dsg.read_value(3, DataType.INT64)
        self.dsg.read_value(4, DataType.INT8)
        self.dsg.read_value(5, DataType.UINT8)
        self.dsg.read_value(6, DataType.U88)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.read_value(-1, DataType.UINT32)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.read_value(constants.MAX_REGISTERS, DataType.UINT32)

        # READ
        self.assertEqual(self.get_next_word(), 0x04140004)
        self.assertEqual(self.get_next_word(), 0x04141008)
        self.assertEqual(self.get_next_word(), 0x04142004)
        self.assertEqual(self.get_next_word(), 0x04143008)
        self.assertEqual(self.get_next_word(), 0x04144001)
        self.assertEqual(self.get_next_word(), 0x04145001)
        self.assertEqual(self.get_next_word(), 0x04146002)

    def test_write_value_from_register(self):
        with self.assertRaises(DataSpecificationNoRegionSelectedException):
            self.dsg.write_value_from_register(0)

        self.dsg.reserve_memory_region(0, 1000)
        self.dsg.switch_write_focus(0)

        self.dsg.write_value_from_register(0)
        self.dsg.write_value_from_register(3)
        self.dsg.write_value_from_register(3, 2)
        self.dsg.write_value_from_register(3, 10, False, DataType.INT8)
        self.dsg.write_value_from_register(3, 0xFF)
        self.dsg.write_value_from_register(0, 0, True)
        self.dsg.write_value_from_register(2, 10, True)
        self.dsg.write_value_from_register(5, 3, True)
        self.dsg.write_value_from_register(5, 3, True, DataType.UINT8)
        self.dsg.write_value_from_register(5, 3, True, DataType.U88)

        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_value_from_register(-1)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_value_from_register(constants.MAX_REGISTERS)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_value_from_register(0, 0)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_value_from_register(0, 256)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_value_from_register(0, -1, True)
        with self.assertRaises(DataSpecificationParameterOutOfBoundsException):
            self.dsg.write_value_from_register(0, constants.MAX_REGISTERS,
                                               True)

        self.skip_words(3)
        # WRITE
        self.assertEqual(self.get_next_word(), 0x04222001)
        self.assertEqual(self.get_next_word(), 0x04222301)
        self.assertEqual(self.get_next_word(), 0x04222302)
        self.assertEqual(self.get_next_word(), 0x0422030A)
        self.assertEqual(self.get_next_word(), 0x042223FF)
        self.assertEqual(self.get_next_word(), 0x04232000)
        self.assertEqual(self.get_next_word(), 0x042322A0)
        self.assertEqual(self.get_next_word(), 0x04232530)
        self.assertEqual(self.get_next_word(), 0x04230530)
        self.assertEqual(self.get_next_word(), 0x04231530)


if __name__ == '__main__':
    unittest.main()
