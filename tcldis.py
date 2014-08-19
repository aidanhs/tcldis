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

class Inst(object):
    def __init__(self, bytecode, loc, *args, **kwargs):
        super(Inst, self).__init__(*args, **kwargs)
        inst_type = INSTRUCTIONS[bytecode.pop(0)]
        self.name = inst_type['name']
        self.ops = []
        for opnum in inst_type['operands']:
            optype = OPERANDS[opnum]
            self.ops.append((optype[0], optype[1](bytecode)))
        self.loc = loc

    def __repr__(self):
        return '<%s: %s %s>' % (
            self.loc if self.loc is not None else '?',
            self.name,
            self.ops
        )

def getinsts(bytecode):
    bytecode = bytecode[:]
    insts = []
    pc = 0
    while len(bytecode) > 0:
        num_bytes = INSTRUCTIONS[bytecode[0]]['num_bytes']
        insts.append(Inst(bytecode[:num_bytes], pc))
        pc += num_bytes
        bytecode = bytecode[num_bytes:]
    return insts

def decompile(tcl_code):
    bytecode = getbc(tcl_code)
    return getinsts(bytecode)
