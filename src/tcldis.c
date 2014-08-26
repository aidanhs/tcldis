#include <Python.h>
#include <tcl.h>
#include <tclCompile.h>
#include "tcl_bcutil.c"

static Tcl_Interp *interp;
static const Tcl_ObjType *tBcType;

#define RUNERR(...) PyErr_Format(PyExc_RuntimeError, ##__VA_ARGS__)

/* Used for converting types */
static int
convSimple(Tcl_Obj *tObj, char** tclString)
{
	int tclStringSize;
	*tclString = Tcl_GetStringFromObj(tObj, &tclStringSize);
	return tclStringSize;
}

static int numTclTypes = 0;
static const Tcl_ObjType **tclType = NULL;
static int (**tclTypeConverter) (Tcl_Obj *, char **) = NULL;

static Tcl_Obj *
getBcTclObj(PyObject *self, PyObject *args, PyObject *kwargs)
{
	static char *kwlist[] = {"tcl_code", "tclobj_ptr", "proc_name", NULL};
	char *tclCode = NULL;
	Py_ssize_t tclObjPtr = 0;
	char *tclProcName = NULL;

	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|sns", kwlist,
			&tclCode, &tclObjPtr, &tclProcName))
		return NULL;

	Tcl_Obj *tObj;

	if (tclCode != NULL) {
		tObj = Tcl_NewObj();
		Tcl_IncrRefCount(tObj);
		Tcl_AppendStringsToObj(tObj, tclCode, NULL);
		/*
		 * This is unusual - even strings failing parsing return ok (and
		 * create a bytecode object detailing the error)
		 */
		if (Tcl_ConvertToType(interp, tObj, tBcType) != TCL_OK) {
			Tcl_DecrRefCount(tObj);
			RUNERR("failed to convert to tcl bytecode");
			return NULL;
		}
	} else if (tclObjPtr != 0) {
		/*
		 * This is pretty dangerous, we get a raw pointer and just take
		 * it on faith that it points to a Tcl_Obj
		 */
		tObj = (Tcl_Obj *)tclObjPtr;
		/* TODO: are we allowed to access typePtr directly? */
		if (tObj->typePtr != tBcType) {
			RUNERR("pointer doesn't point to Tcl_Obj of bytecode");
			return NULL;
		}
		Tcl_IncrRefCount(tObj);
	} else if (tclProcName != NULL) {
		Proc *procPtr = TclFindProc((Interp *)interp, tclProcName);
		if (procPtr == NULL) {
			RUNERR("could not find tcl proc");
			return NULL;
		}
		/* For simplicity, always compile bytecode */
		if (TclProcCompileProc(interp, procPtr,
			procPtr->bodyPtr, procPtr->cmdPtr->nsPtr,
			"body of proc", tclProcName) != TCL_OK) {

			RUNERR("proc compilation failed");
			return NULL;
		}
		tObj = procPtr->bodyPtr;
		Tcl_IncrRefCount(tObj);
	} else {
		RUNERR("must pass an argument to obtain bytecode from");
		return NULL;
	}

	return tObj;
}

static PyObject *
tcldis_printbc(PyObject *self, PyObject *args, PyObject *kwargs)
{
	Tcl_Obj *tObj = getBcTclObj(self, args, kwargs);
	if (tObj == NULL)
		return NULL;

	Tcl_Obj *tStr = TclDisassembleByteCodeObj(tObj);
	Tcl_IncrRefCount(tStr);

	/* If this errors we'll return NULL anyway, don't check explicitly */
	char *str;
	int strsize;
	str = Tcl_GetStringFromObj(tStr, &strsize);
	PyObject *pStr = PyString_FromStringAndSize(str, strsize);

	Tcl_DecrRefCount(tStr);
	Tcl_DecrRefCount(tObj);
	return pStr;
}

static PyObject *
tcldis_getbc(PyObject *self, PyObject *args, PyObject *kwargs)
{
	Tcl_Obj *tObj = getBcTclObj(self, args, kwargs);
	if (tObj == NULL)
		return NULL;

	/*
	 * In 8.6 this changed to tObj->internalRep.twoPtrValue.ptr1. In practice,
	 * this has no effect because of the way the structs are arranged. ptr2 is
	 * currently unused by bytecode tcl objects.
	 */
	ByteCode *bc = tObj->internalRep.otherValuePtr;

	PyObject *pTclVars = PyList_New(0);
	if (pTclVars == NULL)
		return NULL;
	int i, tIdx;
	Tcl_Obj *tLitObj;
	char *tclString;
	int tclStringSize;
	PyObject *pTclVar;
	for (i = 0; i < bc->numLitObjects; i++) {
		tLitObj = bc->objArrayPtr[i];
		pTclVar = NULL;
		if (tLitObj->typePtr == NULL) {
			tclStringSize = convSimple(tLitObj, &tclString);
			if (tclStringSize > -1)
				pTclVar = PyString_FromStringAndSize(tclString, tclStringSize);
		} else {
			for (tIdx = 0; tIdx < numTclTypes; tIdx++) {
				if (tLitObj->typePtr != tclType[tIdx])
					continue;
				tclStringSize = (*(tclTypeConverter[tIdx]))(tLitObj, &tclString);
				if (tclStringSize > -1)
					pTclVar = PyString_FromStringAndSize(tclString, tclStringSize);
				break;
			}
			if (pTclVar == NULL) {
				RUNERR("Unknown Tcl type %s", tLitObj->typePtr->name);
			}
		}
		if (pTclVar == NULL || PyList_Append(pTclVars, pTclVar) != 0) {
			Py_CLEAR(pTclVar);
			Py_CLEAR(pTclVars);
			break;
		}
	}

	/* If this errors we'll return NULL anyway, don't check explicitly */
	/* The cast is fine because Python treats bytearrays as unsigned */
	PyObject *pBuf = PyByteArray_FromStringAndSize(
		(char *)bc->codeStart, bc->numCodeBytes);

	Tcl_DecrRefCount(tObj);

	if (pTclVars == NULL || pBuf == NULL) {
		Py_CLEAR(pTclVars);
		Py_CLEAR(pBuf);
		return NULL;
	}
	return Py_BuildValue("NN", pBuf, pTclVars);
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
	int i = 0, opIdx;
	PyObject *pInst = NULL;
	PyObject *pInstName = NULL;
	PyObject *pInstNumBytes = NULL;
	PyObject *pInstStackEffect = NULL;
	PyObject *pInstOperands = NULL, *pInstOperand = NULL;
	while (1) {
		inst = insts[i];
		if (inst.name == NULL)
			break;

		pInst = PyDict_New();
		if (pInst == NULL)
			goto err;

		pInstName = PyString_FromString(inst.name);
		if (pInstName == NULL)
			goto err;
		if (PyDict_SetItemString(pInst, "name", pInstName) != 0)
			goto err;
		Py_CLEAR(pInstName);

		pInstNumBytes = PyInt_FromLong(inst.numBytes);
		if (pInstNumBytes == NULL)
			goto err;
		if (PyDict_SetItemString(pInst, "num_bytes", pInstNumBytes) != 0)
			goto err;
		Py_CLEAR(pInstNumBytes);

		if (inst.stackEffect == INT_MIN) {
			pInstStackEffect = PyString_FromString("op1");
		} else {
			pInstStackEffect = PyInt_FromLong(inst.stackEffect);
		}
		if (pInstStackEffect == NULL)
			goto err;
		if (PyDict_SetItemString(pInst, "stack_effect", pInstStackEffect) != 0)
			goto err;
		Py_CLEAR(pInstStackEffect);

		pInstOperands = PyList_New(0);
		if (pInstOperands == NULL)
			goto err;
		for (opIdx = 0; opIdx < inst.numOperands; opIdx++) {
			pInstOperand = PyInt_FromLong(inst.opTypes[opIdx]);
			if (pInstOperand == NULL)
				goto err;
			if (PyList_Append(pInstOperands, pInstOperand) != 0)
				goto err;
			Py_CLEAR(pInstOperand);
		}
		if (PyDict_SetItemString(pInst, "operands", pInstOperands) != 0)
			goto err;
		Py_CLEAR(pInstOperands);

		if (PyList_Append(pInsts, pInst) != 0)
			goto err;

		i++;
	}

	return pInsts;

err:
	Py_XDECREF(pInsts);
	Py_XDECREF(pInst);
	Py_XDECREF(pInstName);
	Py_XDECREF(pInstNumBytes);
	Py_XDECREF(pInstStackEffect);
	Py_XDECREF(pInstOperands); Py_XDECREF(pInstOperand);
	return NULL;
}

static PyObject *
tcldis_literal_convert(PyObject *self, PyObject *args, PyObject *kwargs)
{
	static char *kwlist[] = {"type_name", "conv_fn_ptr", NULL};
	char *typeName = NULL;
	Py_ssize_t convFnPtr = 0;

	if (!PyArg_ParseTupleAndKeywords(args, kwargs, "|sn", kwlist,
			&typeName, &convFnPtr))
		return NULL;

	int i;

	/* TODO: if no args are specified, return current details */
	if (typeName == NULL && convFnPtr == 0) {
		PyObject *pTclTypes = PyList_New(0);
		if (pTclTypes == NULL)
			return NULL;
		PyObject *pTclType;
		for (i = 0; i < numTclTypes; i++) {
			pTclType = Py_BuildValue("sn",
				tclType[i]->name,
				(Py_ssize_t)tclTypeConverter[i]
			);
			if (pTclType == NULL || PyList_Append(pTclTypes, pTclType) != 0) {
				Py_CLEAR(pTclType);
				Py_CLEAR(pTclTypes);
				break;
			}
		}
		return pTclTypes;
	}

	if (typeName == NULL || convFnPtr == 0) {
		RUNERR("Must pass type name and conversion function pointer");
		return NULL;
	}

	for (i = 0; i < numTclTypes; i++) {
		if (strcmp(typeName, tclType[i]->name) != 0)
			continue;
		tclTypeConverter[i] =
			(int (*) (Tcl_Obj *, char **))convFnPtr;
		break;
	}
	if (i == numTclTypes) {
		RUNERR("Could not find type name");
		return NULL;
	}

	return Py_BuildValue("O", Py_None);
}

static PyMethodDef TclDisMethods[] = {
	{"printbc",  (PyCFunction)tcldis_printbc,
		METH_VARARGS | METH_KEYWORDS,
		"Given some Tcl code, format and print the bytecode."},
	{"getbc",  (PyCFunction)tcldis_getbc,
		METH_VARARGS | METH_KEYWORDS,
		"Given some Tcl code, get the bytecode as a bytearray."},
	{"inst_table",  (PyCFunction)tcldis_inst_table,
		METH_VARARGS | METH_KEYWORDS,
		"Get the instruction table for Tcl bytecode."},
	{"literal_convert",  (PyCFunction)tcldis_literal_convert,
		METH_VARARGS | METH_KEYWORDS,
		"Set the converter for a type of literal value."},
	{NULL, NULL, 0, NULL} /* Sentinel */
};

/* Module name is _tcldis */
PyMODINIT_FUNC
init_tcldis(void)
{
	interp = PyCapsule_Import("tclpy.interp", 0);
	if (interp == NULL) {
		PyErr_Clear();
		interp = Tcl_CreateInterp();
	}

	tBcType = Tcl_GetObjType("bytecode");

	Tcl_Obj *tTypes = Tcl_NewObj();
	Tcl_IncrRefCount(tTypes);
	if (Tcl_AppendAllObjTypes(interp, tTypes) != TCL_OK ||
			Tcl_ListObjLength(interp, tTypes, &numTclTypes) != TCL_OK) {
		Tcl_DecrRefCount(tTypes);
		RUNERR("could not get list of Tcl types");
		return;
	};

	tclType = malloc(numTclTypes*sizeof(*tclType));
	tclTypeConverter = malloc(numTclTypes*sizeof(*tclTypeConverter));
	int i;
	Tcl_Obj *tType;
	for (i = 0; i < numTclTypes; i++) {
		Tcl_ListObjIndex(interp, tTypes, i, &tType);
		tclType[i] = Tcl_GetObjType(Tcl_GetString(tType));
		tclTypeConverter[i] = convSimple;
	}

	Tcl_DecrRefCount(tTypes);

	PyObject *m = Py_InitModule("_tcldis", TclDisMethods);
	if (m == NULL)
		return;
}


