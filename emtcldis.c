#include <Python.h>

// Modules
static PyObject *pyjson;
static PyObject *pytclpy;
static PyObject *pytcldis;

// Each of the 4 functions
static PyObject *pystr_eval;

static PyObject *pyfn_getbc;
static PyObject *pytuple_empty;
static PyObject *pydict_prockw;

static PyObject *pystr_decompile_steps;

static PyObject *pystr_dumps;

// Global variables
static char *error = "ERROR";
static PyObject *json = NULL;

int emtcldis_init() {
    pyjson = PyImport_ImportModule("json");
    pytclpy = PyImport_ImportModule("tclpy");
    pytcldis = PyImport_ImportModule("tcldis");

    // For eval
    pystr_eval = PyString_FromString("eval");

    // For getbc
    pyfn_getbc = PyObject_GetAttrString(pytcldis, "getbc");
    pytuple_empty = PyTuple_New(0);
    pydict_prockw = PyDict_New();
    PyDict_SetItemString(pydict_prockw, "proc_name", PyString_FromString("p"));

    // For decompile_steps
    pystr_decompile_steps = PyString_FromString("decompile_steps");

    // For json dump
    pystr_dumps = PyString_FromString("dumps");

    return 0;
}

char *emtcldis_decompile(const char *code) {
    PyObject *pycode, *nil, *bc, *res, *json;

    pycode = PyString_FromString(code);
    if (pycode == NULL) return "E0";

    nil = PyObject_CallMethodObjArgs(pytclpy, pystr_eval, pycode, NULL);
    if (nil == NULL) return "E1";
    Py_DECREF(nil);

    bc = PyObject_Call(pyfn_getbc, pytuple_empty, pydict_prockw);
    if (bc == NULL) return "E2";

    res = PyObject_CallMethodObjArgs(pytcldis, pystr_decompile_steps, bc, NULL);
    Py_DECREF(bc);
    if (res == NULL) return "E3";

    Py_CLEAR(json); // Free before use to avoid mem leak
    json = PyObject_CallMethodObjArgs(pyjson, pystr_dumps, res, NULL);
    Py_DECREF(res);
    if (json == NULL) return "E4";

    return PyString_AS_STRING(json);
}
