import copy

from aql_testcase import AqlTestCase

from aql.options import OptionType, EnumOptionType, RangeOptionType,\
    ListOptionType, OptionValue, ConditionalValue, Condition,\
    SimpleInplaceOperation, op_set, op_iadd, op_isub,\
    ErrorOptionTypeUnableConvertValue


# ==============================================================================


def _condition(options, context, flag, opt_value=None):
    return flag


def _convert_value(options, context, value):
    if isinstance(value, OptionValue):
        value = value.get(options, context, _convert_value)

    return value


class TestOptionValue(AqlTestCase):

    # -------------------------------------------------------------------------------

    def test_option_value(self):
        opt_type1 = RangeOptionType(min_value=0, max_value=5)

        opt_value = OptionValue(opt_type1)

        cond = Condition(None, _condition, flag=True, opt_value=opt_value)
        cond_value = ConditionalValue(op_iadd(2), cond)
        cond_value2 = ConditionalValue(op_iadd(3), cond)
        cond_value3 = ConditionalValue(op_iadd(3), cond)

        opt_value.append_value(cond_value)
        opt_value.append_value(cond_value2)
        opt_value.append_value(cond_value3)

        self.assertEqual(opt_value.get(options={}, context=None), 5)

    # -------------------------------------------------------------------------------

    def test_option_value2(self):
        opt_value = OptionValue(OptionType(int))

        cond_true = Condition(None, _condition, flag=True)
        cond_false = Condition(cond_true,  _condition, flag=False)
        cond_false = Condition(cond_false, _condition, flag=True)

        opt_value.append_value(ConditionalValue(op_iadd(2), cond_false))
        self.assertEqual(opt_value.get({}, None), 0)

        opt_value.append_value(ConditionalValue(op_iadd(3), cond_true))
        self.assertEqual(opt_value.get({}, None), 3)

        opt_value.append_value(ConditionalValue(op_iadd(1), cond_true))
        self.assertEqual(opt_value.get({}, None), 4)

        opt_value.append_value(ConditionalValue(op_iadd(1), cond_false))
        self.assertEqual(opt_value.get({}, None), 4)

        opt_value2 = OptionValue(OptionType(int))

        opt_value.append_value(
            ConditionalValue(op_set(opt_value2), cond_true))

        opt_value2.append_value(ConditionalValue(op_set(7), cond_true))

        self.assertEqual(opt_value.get({}, None, _convert_value), 7)
        self.assertEqual(opt_value2.get({}, None, _convert_value), 7)

        opt_value2.append_value(ConditionalValue(op_set(8), cond_true))

        self.assertEqual(opt_value.get({}, None, _convert_value), 8)
        self.assertEqual(opt_value2.get({}, None, _convert_value), 8)

        opt_value.append_value(ConditionalValue(op_isub(0), cond_true))

        self.assertEqual(opt_value.get({}, None, _convert_value), 8)

        tmp_opt_value = opt_value.copy()

        self.assertEqual(tmp_opt_value.get({}, None, _convert_value), 8)

        tmp_opt_value.append_value(ConditionalValue(op_iadd(2), cond_true))

        self.assertEqual(tmp_opt_value.get({}, None, _convert_value), 10)

    # -------------------------------------------------------------------------------

    def test_option_value3(self):
        opt_value = OptionValue(OptionType(int))

        opt_value.append_value(ConditionalValue(op_set(1)))
        self.assertEqual(opt_value.get({}, None), 1)
        opt_value.append_value(ConditionalValue(op_set(0)))
        self.assertEqual(opt_value.get({}, None), 0)

        opt_value_list = OptionValue(ListOptionType(value_type=int))
        opt_value_list.append_value(ConditionalValue(op_set(1)))
        self.assertEqual(opt_value_list.get({}, None), 1)

        opt_value_list.append_value(ConditionalValue(op_iadd(0)))
        self.assertEqual(opt_value_list.get({}, None), "1, 0")

    # -------------------------------------------------------------------------------

    def test_option_value4(self):
        def _inc_value(value):
            return value + 1

        opt_value = OptionValue(OptionType(int))
        opt_value.append_value(ConditionalValue(op_set(2)))
        opt_value.append_value(
            ConditionalValue(SimpleInplaceOperation(_inc_value)))

        self.assertEqual(opt_value.get({}, None), 3)

    # -------------------------------------------------------------------------------

    def test_option_value_enum(self):
        value_type = EnumOptionType(
            values=(('off', 0), ('size', 1), ('speed', 2)))

        opt_value = OptionValue(value_type)

        opt_value.append_value(ConditionalValue(op_set('size')))
        self.assertEqual(opt_value.get({}, None), value_type(1))

        opt_value.append_value(ConditionalValue(op_set('ultra')))
        self.assertRaises(
            ErrorOptionTypeUnableConvertValue, opt_value.get, {}, None)

    # -------------------------------------------------------------------------------

    def test_option_value_cyclic(self):
        opt_value1 = OptionValue(OptionType(value_type=int))
        opt_value2 = OptionValue(RangeOptionType(min_value=0, max_value=5))

        opt_value1.append_value(ConditionalValue(op_set(1)))
        self.assertEqual(opt_value1.get({}, None, _convert_value), 1)

        opt_value2.append_value(ConditionalValue(op_set(2)))
        self.assertEqual(opt_value2.get({}, None, _convert_value), 2)

        opt_value1.append_value(ConditionalValue(op_iadd(opt_value2)))
        self.assertEqual(opt_value1.get({}, None, _convert_value), 3)

        opt_value2.append_value(ConditionalValue(op_iadd(opt_value1)))

        self.assertEqual(opt_value2.get({}, None, _convert_value), 5)

        opt_value1.append_value(ConditionalValue(op_iadd(opt_value2)))

        self.assertEqual(opt_value2.get({}, None, _convert_value),
                         opt_value2.option_type(7))

        self.assertEqual(opt_value1.get({}, None, _convert_value), 7)

        # opt1: 1 + opt2 + opt2 = 1 + 3 + 3
        # opt2: 2 + opt1 = 2 + 1 + 2 + 2

    # -------------------------------------------------------------------------------

    def test_option_value_list(self):

        opt_type1 = ListOptionType(value_type=EnumOptionType(
            values=(('off', 0), ('size', 1), ('speed', 2))))

        opt_value = OptionValue(opt_type1)

        cond = Condition(None, _condition, flag=True, opt_value=opt_value)
        cond2 = Condition(cond, _condition, flag=False, opt_value=opt_value)

        cond_value = ConditionalValue(op_iadd(1), cond)
        cond_value2 = ConditionalValue(op_iadd(0), cond2)
        cond_value3 = ConditionalValue(op_iadd(2), cond)
        cond_value4 = ConditionalValue(op_iadd(1), cond2)

        opt_value.append_value(cond_value)
        opt_value.append_value(cond_value2)
        opt_value.append_value(cond_value3)
        opt_value.append_value(cond_value4)

        self.assertEqual(opt_value.get({}, None), [1, 2])

        opt_value.prepend_value(cond_value3)
        self.assertEqual(opt_value.get({}, None), [2, 1, 2])

        opt_value = copy.copy(opt_value)
        self.assertEqual(opt_value.get({}, None), [2, 1, 2])

        self.assertIs(opt_value.option_type, opt_type1)

    # -------------------------------------------------------------------------------

    def test_option_value_dict(self):
        opt_type1 = OptionType(value_type=dict)

        opt_value = OptionValue(opt_type1)

        cond_value = ConditionalValue(op_set({3: 4}))

        opt_value.append_value(cond_value)

        self.assertEqual(opt_value.get({}, None), {3: 4})
