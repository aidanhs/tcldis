#include <Python.h>
#include <tcl.h>
#include <tclCompile.h>

static Tcl_Interp *interp;
extern const void *TclGetInstructionTable(void);

static PyObject *
tcldis_test(PyObject *self, PyObject *args, PyObject *kwargs)
{
	static char *kwlist[] = {NULL};

	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "", kwlist))
		return NULL;

	Tcl_Obj *tObj = Tcl_NewObj();
	Tcl_AppendStringsToObj(tObj, "puts 1", NULL);

	const Tcl_ObjType *bct = Tcl_GetObjType("bytecode");
	if (Tcl_ConvertToType(interp, tObj, bct) != TCL_OK)
		return PyLong_FromLong(1);

	return PyLong_FromLong(0);
}

static PyObject *
tcldis_inst_table(PyObject *self, PyObject *args, PyObject *kwargs)
{
	static char *kwlist[] = {NULL};

	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "", kwlist))
		return NULL;

	const InstructionDesc *insts =
		(const InstructionDesc *)TclGetInstructionTable();

	PyObject *pInsts = PyList_New(0);
	if (pInsts == NULL)
		return NULL;

	InstructionDesc inst;
	int i = 0;
	PyObject *pStr;
	while (1) {
		inst = insts[i];
		if (inst.name == NULL)
			break;
		pStr = PyString_FromString(inst.name);
		if (pStr == NULL) {
			Py_DECREF(pInsts);
			return NULL;
		}
		if (PyList_Append(pInsts, pStr) != 0) {
			Py_DECREF(pStr);
			Py_DECREF(pInsts);
			return NULL;
		}
		Py_DECREF(pStr);
		i++;
	}

	return pInsts;
}

static PyMethodDef TclDisMethods[] = {
	{"test",  (PyCFunction)tcldis_test,
		METH_VARARGS | METH_KEYWORDS, "test"},
	{"inst_table",  (PyCFunction)tcldis_inst_table,
		METH_VARARGS | METH_KEYWORDS, "inst_table"},
	{NULL, NULL, 0, NULL} /* Sentinel */
};

/* Module name is _tcldis */
PyMODINIT_FUNC
init_tcldis(void)
{
	interp = Tcl_CreateInterp();

	PyObject *m = Py_InitModule("_tcldis", TclDisMethods);
	if (m == NULL)
		return;
}


