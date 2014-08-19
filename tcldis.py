from __future__ import print_function

import struct

import _tcldis
printbc = _tcldis.printbc
getbc = _tcldis.getbc

INSTRUCTIONS = _tcldis.inst_table()

# InstOperandType from tclCompile.h
OPERANDS = [
    ('NONE',  None), # Should never be present
    ('INT1',  lambda ba: struct.unpack('>b', ''.join([chr(ba.pop(0)) for i in range(1)]))),
    ('INT4',  lambda ba: struct.unpack('>i', ''.join([chr(ba.pop(0)) for i in range(4)]))),
    ('UINT1', lambda ba: struct.unpack('>B', ''.join([chr(ba.pop(0)) for i in range(1)]))),
    ('UINT4', lambda ba: struct.unpack('>I', ''.join([chr(ba.pop(0)) for i in range(4)]))),
    ('IDX4',  lambda ba: struct.unpack('>i', ''.join([chr(ba.pop(0)) for i in range(4)]))),
    ('LVT1',  lambda ba: struct.unpack('>B', ''.join([chr(ba.pop(0)) for i in range(1)]))),
    ('LVT4',  lambda ba: struct.unpack('>I', ''.join([chr(ba.pop(0)) for i in range(4)]))),
    ('AUX4',  lambda ba: struct.unpack('>I', ''.join([chr(ba.pop(0)) for i in range(4)]))),
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
