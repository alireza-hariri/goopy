from go4py.types import Variable, VarType, GoStringType

need_c_convert = [GoStringType]


def indent(str, indent=4):
    return "\n".join([(indent * " " + line) if line else "" for line in str.split("\n")])


class ItemConverter:
    def __init__(
        self,
        item_type: VarType,
        free_resource_code: str,
        item_name="item",
        # indent = 0,
    ):
        self.t = item_type
        self.name = item_name
        self.free_resource_code = indent(free_resource_code, 8)

    def check_and_convert(self):
        pytype = self.t.check("").split("_Check")[0]  # TODO: this is hacky fix it
        result = f"""if (!{self.t.check(self.name)}) {{
            PyErr_SetString(PyExc_TypeError, "List items must be {pytype}");{self.free_resource_code}
            return NULL;
        }}"""
        if self.t.need_copy:
            result += f"\n        {self.t.c_type()} c_{self.name} = {self.t.from_py_converter(self.name)};"
        return result

    def final_value(self):
        if self.t.need_copy:
            match self.t:
                case GoStringType():
                    return f"(GoString) {{c_{self.name}, (GoInt)strlen(c_{self.name})}}"
                case _:
                    raise Exception("Not implemented")
        else:
            return self.t.from_py_converter(self.name)


def go_slice_from_py_list(inp_var: Variable, other_free_code=""):
    name = inp_var.name
    free_logic = f"""{other_free_code}
    free({name}_CArray);"""
    item_conv = ItemConverter(inp_var.type.item_type, free_logic, "item")
    copy_logic = f"""
    if (!PyList_Check({name})) {{
        PyErr_SetString(PyExc_TypeError, "Argument {name} must be a list");{indent(other_free_code)}
        return NULL;
    }}
    int len = PyList_Size({name});
    {inp_var.type.cgo_type()} {name}_CArray = malloc(len * sizeof({inp_var.type.item_type.cgo_type()}));
    for (int i = 0; i < len; i++) {{
        PyObject* item = PyList_GetItem(strs, i);
        {item_conv.check_and_convert()}
        {name}_CArray[i] = {item_conv.final_value()};
    }}
    if (PyErr_Occurred()) {{{indent(free_logic)}
        return NULL;
    }}
    GoSlice go_{name} = {{{name}_CArray, (GoInt)len, (GoInt)len}};"""
    return copy_logic, free_logic
