from __future__ import print_function

import struct

import _tcldis
printbc = _tcldis.printbc
getbc = _tcldis.getbc

INSTRUCTIONS = _tcldis.inst_table()

def getop(numbytes, optype):
    def getop_lambda(bc):
        opbytes = ''.join([chr(bc.pop(0)) for i in range(numbytes)])
        return struct.unpack(optype, opbytes)[0]
    return getop_lambda

# InstOperandType from tclCompile.h
OPERANDS = [
    ('NONE',  None), # Should never be present
    ('INT1',  getop(1,'>b')),
    ('INT4',  getop(4,'>i')),
    ('UINT1', getop(1,'>B')),
    ('UINT4', getop(4,'>I')),
    ('IDX4',  getop(4,'>i')),
    ('LVT1',  getop(1,'>B')),
    ('LVT4',  getop(4,'>I')),
    ('AUX4',  getop(4,'>I')),
]

def getinst(bc):
    inst = INSTRUCTIONS[bc.pop(0)]
    ops = []
    for opnum in inst['operands']:
        optype = OPERANDS[opnum]
        ops.append((optype[0], optype[1](bc)))
    return (inst['name'], tuple(ops))

def decompile(tcl_code):
    bc = getbc(tcl_code)
    insts = []
    while len(bc) > 0:
        oldlen = len(bc)
        insts.append(getinst(bc))
    return insts
