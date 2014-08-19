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
    def __init__(self, *args, **kwargs):
        super(Inst, self).__init__(*args, **kwargs)
        self.name = None
        self.ops = []
        self.loc = None
    def __repr__(self):
        return '<%s: %s %s>' % (
            self.loc if self.loc is not None else '?',
            self.name,
            self.ops
        )

def getinst(bc, pc=None):
    insttype = INSTRUCTIONS[bc.pop(0)]
    inst = Inst()
    inst.name = insttype['name']
    inst.loc = pc
    for opnum in insttype['operands']:
        optype = OPERANDS[opnum]
        inst.ops.append((optype[0], optype[1](bc)))
    return inst

def getinsts(tcl_code):
    bc = getbc(tcl_code)
    insts = []
    pc = 0
    while len(bc) > 0:
        oldlen = len(bc)
        inst = getinst(bc, pc)
        insts.append(inst)
        pc += oldlen - len(bc)
    return insts

def decompile(tcl_code):
    return getinsts(tcl_code)
