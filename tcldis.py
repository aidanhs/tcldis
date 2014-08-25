from __future__ import print_function

import struct
import copy

import _tcldis
printbc = _tcldis.printbc
getbc = _tcldis.getbc
literal_convert = _tcldis.literal_convert

INSTRUCTIONS = _tcldis.inst_table()
JUMP_INSTRUCTIONS = (
    'jump1', 'jump4', 'jumpTrue1', 'jumpTrue4', 'jumpFalse1', 'jumpFalse4'
)

def _getop(optype):
    """
    Given a C struct descriptor, return a function which will take the necessary
    bytes off the front of a bytearray and return the python value.
    """
    def getop_lambda(bc):
        # The 'standard' sizes in the struct module match up to what Tcl expects
        numbytes = struct.calcsize(optype)
        opbytes = ''.join([chr(bc.pop(0)) for i in range(numbytes)])
        return struct.unpack(optype, opbytes)[0]
    return getop_lambda

# InstOperandType from tclCompile.h
OPERANDS = [
    ('NONE',  None), # Should never be present
    ('INT1',  _getop('>b')),
    ('INT4',  _getop('>i')),
    ('UINT1', _getop('>B')),
    ('UINT4', _getop('>I')),
    ('IDX4',  _getop('>i')),
    ('LVT1',  _getop('>B')),
    ('LVT4',  _getop('>I')),
    ('AUX4',  _getop('>I')),
]

# Tcl bytecode instruction
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
        # Note that this doesn't get printed on str() so we only see
        # the value when it gets reduced to a BCJump class
        if self.name in JUMP_INSTRUCTIONS:
            self.targetloc = self.loc + self.ops[0][1]

    def __repr__(self):
        return '<%s: %s %s>' % (
            self.loc if self.loc is not None else '?',
            self.name,
            self.ops
        )

#################################################################
# My own representation of anything that can be used as a value #
#################################################################

# The below represent my interpretation of the Tcl stack machine
class BCValue(object):
    def __init__(self, inst, value, *args, **kwargs):
        super(BCValue, self).__init__(*args, **kwargs)
        assert all([v.stack() == 1 for v in value if isinstance(v, BCValue)])
        self.inst = inst
        self.value = value
        self._stackn = 1
    def stack(self, n=None):
        if n is None:
            return self._stackn
        try:
            assert any([isinstance(self, bctype) for bctype in _destackable_bctypes])
        except AssertionError:
            print('Unrecognised pop of %s, please report.' % (self,))
            raise
        assert n == -1
        assert self._stackn == 1
        self._stackn -= 1
    def __repr__(self): assert False
    def fmt(self): assert False

class BCLiteral(BCValue):
    def __init__(self, *args, **kwargs):
        super(BCLiteral, self).__init__(*args, **kwargs)
    def __repr__(self):
        return 'BCLiteral(%s)' % (repr(self.value),)
    def fmt(self):
        val = self.value
        if val == '': return '{}'
        if not any([c in val for c in '[]{}""\f\r\n\t\v ']):
            return val

        # Can't use simple case, go the hard route
        matching_brackets = True
        bracket_level = 0
        for c in val:
            if c == '{': bracket_level += 1
            elif c == '}': bracket_level -= 1
            if bracket_level < 0:
                matching_brackets = False
                break
        # If we need escape codes we have to use ""
        # Note we don't try and match \n or \t - these are probably used
        # in multiline strings, so if possible use {} quoting and print
        # them literally.
        if any([c in val for c in '\f\r\v']) or not matching_brackets:
            val = (val
                .replace('\\', '\\\\')
                .replace('\f', '\\f')
                .replace('\r', '\\r')
                .replace('\n', '\\n')
                .replace('\t', '\\t')
                .replace('\v', '\\v')
                .replace('}', '\\}')
                .replace('{', '\\{')
                .replace('"', '\\"')
                .replace('"', '\\"')
                .replace('[', '\\[')
                .replace(']', '\\]')
            )
            val = '"' + val + '"'
        else:
            val = '{' + val + '}'
        return val

class BCVarRef(BCValue):
    def __init__(self, *args, **kwargs):
        super(BCVarRef, self).__init__(*args, **kwargs)
        assert len(self.value) == 1
    def __repr__(self):
        return 'BCVarRef(%s)' % (repr(self.value),)
    def fmt(self):
        return '$' + self.value[0].fmt()

class BCArrayRef(BCValue):
    def __init__(self, *args, **kwargs):
        super(BCArrayRef, self).__init__(*args, **kwargs)
        assert len(self.value) == 2
    def __repr__(self):
        return 'BCArrayRef(%s)' % (repr(self.value),)
    def fmt(self):
        return '$' + self.value[0].fmt() + '(' + self.value[1].fmt() + ')'

class BCProcCall(BCValue):
    def __init__(self, *args, **kwargs):
        super(BCProcCall, self).__init__(*args, **kwargs)
        assert len(self.value) >= 1
    def __repr__(self):
        return 'BCProcCall(%s)' % (self.value,)
    def fmt(self):
        args = self.value[:]
        if args[0].fmt() == '::tcl::array::set':
            args[0:1] = [BCLiteral(None, 'array'), BCLiteral(None, 'set')]
        cmd = ' '.join([arg.fmt() for arg in args])
        if self.stack():
            cmd = '[' + cmd + ']'
        return cmd

class BCReturn(BCValue):
    def __init__(self, *args, **kwargs):
        super(BCReturn, self).__init__(*args, **kwargs)
        assert len(self.value) == 2
        assert self.value[1].value == '' # Options
        assert self.inst.ops[0][1] == 0 # Code
        assert self.inst.ops[1][1] == 1 # Level
    def __repr__(self):
        return 'BCReturn(%s)' % (repr(self.value),)
    def fmt(self):
        if self.value[0].value == '': return 'return'
        return 'return ' + self.value[0].fmt()

class BCIf(BCValue):
    def __init__(self, *args, **kwargs):
        super(BCIf, self).__init__(*args, **kwargs)
        assert len(self.value) == len(self.inst) == 2
        assert all([isinstance(jump, BCJump) for jump in self.inst])
        assert self.inst[0].on in (True, False) and self.inst[1].on is None
        # An if condition takes 'ownership' of the values returned in any
        # of its branches
        for bblock in self.value:
            inst = bblock.insts[-1]
            if isinstance(inst, BCLiteral):
                assert inst.value == ''
                bblock.insts[-1:] = []
            else:
                inst.stack(-1)
    def __repr__(self):
        return 'BCIf(%s)' % (self.value,)
    def fmt(self):
        conditionstr = self.inst[0].value[0].fmt()
        if self.inst[0].on is True:
            conditionstr = '!' + conditionstr
        cmd = (
            'if {%s} {' +
            '\n\t' + self.value[0].fmt().replace('\n', '\n\t') + '\n' +
            '} else {' +
            '\n\t' + self.value[1].fmt().replace('\n', '\n\t') + '\n' +
            '}'
        ) % (conditionstr,)
        if self.stack():
            cmd = '[' + cmd + ']'
        return cmd

_destackable_bctypes = [BCProcCall, BCIf, BCReturn]

####################################################################
# My own representation of anything that cannot be used as a value #
####################################################################

class BCNonValue(object):
    def __init__(self, inst, value, *args, **kwargs):
        super(BCNonValue, self).__init__(*args, **kwargs)
        self.inst = inst
        self.value = value
    def __repr__(self): assert False
    def fmt(self): assert False

class BCJump(BCNonValue):
    def __init__(self, on, *args, **kwargs):
        super(BCJump, self).__init__(*args, **kwargs)
        assert len(self.value) == 0 if on is None else 1
        self.on = on
        self.targetloc = self.inst.targetloc
    def __repr__(self):
        condition = ''
        if self.on is not None:
            condition = '(%s==%s)' % (self.on, self.value)
        return 'BCJump%s->%s' % (condition, self.inst.targetloc)
    def fmt(self):
        #return 'JUMP%s(%s)' % (self.on, self.value[0].fmt())
        return str(self)

# Just a formatting container for the form a(x)
class BCArrayElt(BCNonValue):
    def __init__(self, *args, **kwargs):
        super(BCArrayElt, self).__init__(*args, **kwargs)
        assert len(self.value) == 2
    def __repr__(self):
        return 'BCArrayElt(%s)' % (repr(self.value),)
    def fmt(self):
        return self.value[0].fmt() + '(' + self.value[1].fmt() + ')'

##############################
# Any basic block structures #
##############################

# Basic block, containing a linear flow of logic
class BBlock(object):
    def __init__(self, insts, loc, *args, **kwargs):
        super(BBlock, self).__init__(*args, **kwargs)
        self.insts = insts
        self.loc = loc
    def __repr__(self):
        return 'BBlock(at %s, %s insts)' % (self.loc, len(self.insts))
    def fmt(self):
        return '\n'.join([
            inst.fmt() if not isinstance(inst, Inst) else str(inst)
            for inst in self.insts
        ])

########################
# Functions start here #
########################

def getinsts(bytecode):
    """
    Given bytecode in a bytearray, return a list of Inst objects.
    """
    bytecode = bytecode[:]
    insts = []
    pc = 0
    while len(bytecode) > 0:
        num_bytes = INSTRUCTIONS[bytecode[0]]['num_bytes']
        insts.append(Inst(bytecode[:num_bytes], pc))
        pc += num_bytes
        bytecode = bytecode[num_bytes:]
    return insts

def _bblock_create(insts):
    """
    Given a list of Inst objects, split them up into basic blocks.
    """
    # Identify the beginnings and ends of all basic blocks
    starts = set()
    ends = set()
    newstart = True
    for i, inst in enumerate(insts):
        if newstart:
            starts.add(inst.loc)
            newstart = False
        if inst.name in JUMP_INSTRUCTIONS:
            ends.add(inst.loc)
            starts.add(inst.targetloc)
            newstart = True
            # inst before target inst is end of a bblock
            # search through instructions for instruction before the target
            if inst.targetloc != 0:
                instbeforeidx = 0
                while True:
                    if insts[instbeforeidx+1].loc == inst.targetloc: break
                    instbeforeidx += 1
                instbefore = insts[instbeforeidx]
                ends.add(instbefore.loc)
    ends.add(insts[-1].loc)
    # Create the basic blocks
    assert len(starts) == len(ends)
    bblocks = []
    bblocks_insts = insts[:]
    for start, end in zip(sorted(list(starts)), sorted(list(ends))):
        bbinsts = []
        assert bblocks_insts[0].loc == start
        while bblocks_insts[0].loc < end:
            bbinsts.append(bblocks_insts.pop(0))
        assert bblocks_insts[0].loc == end
        bbinsts.append(bblocks_insts.pop(0))
        bblocks.append(BBlock(bbinsts, bbinsts[0].loc))
    # Jump fixup
    for inst in insts:
        if inst.name not in JUMP_INSTRUCTIONS:
            continue
        for bblock in bblocks:
            if inst.targetloc == bblock.loc:
                inst.targetloc = bblock
                break
        else:
            assert False
    return bblocks

def _inst_reductions():
    """
    Define how each instruction is reduced to one of my higher level
    representations.
    """
    def N(n): return lambda _: n
    firstop = lambda inst: inst.ops[0][1]
    def destack(v): v.stack(-1); return v
    def can_destack(arg):
        return any([
            isinstance(arg, bctype)
            for bctype in _destackable_bctypes
        ])
    def is_simple(arg):
        return any([
            isinstance(arg, bctype)
            for bctype in [BCLiteral, BCVarRef, BCArrayRef]
        ])
    inst_reductions = {
        # Callers
        'invokeStk1': {'nargs': firstop, 'redfn': BCProcCall},
        'invokeStk4': {'nargs': firstop, 'redfn': BCProcCall},
        'listLength': {'nargs': N(1), 'redfn': lambda inst, kv: BCProcCall(inst, [BCLiteral(None, 'llength'), kv[0]])},
        'incrStkImm': {'nargs': N(1), 'redfn': lambda inst, kv: BCProcCall(inst, [BCLiteral(None, 'incr'), kv[0]] + ([BCLiteral(None, str(inst.ops[0][1]))] if inst.ops[0][1] != 1 else []))},
        # Jumps
        'jump1': {'nargs': N(0), 'redfn': lambda i, v: BCJump(None, i, v)},
        'jumpFalse1': {'nargs': N(1), 'redfn': lambda i, v: BCJump(False, i, v)},
        'jumpTrue1': {'nargs': N(1), 'redfn': lambda i, v: BCJump(True, i, v)},
        # Variable references
        'loadArrayStk': {'nargs': N(2), 'redfn': BCArrayRef},
        'loadStk': {'nargs': N(1), 'redfn': BCVarRef},
        # Variable sets
        'storeStk': {'nargs': N(2), 'redfn': lambda inst, kv: BCProcCall(inst, [BCLiteral(None, 'set'), kv[0], kv[1]])},
        'storeArrayStk': {'nargs': N(3), 'redfn': lambda inst, kv: BCProcCall(inst, [BCLiteral(None, 'set'), BCArrayElt(None, kv[:2]), kv[2]])},
        # Value ignoring
        'done': {'nargs': N(1), 'redfn': lambda i, v: destack(v[0]), 'checkfn': can_destack},
        'pop': {'nargs': N(1), 'redfn': lambda i, v: destack(v[0]), 'checkfn': can_destack},
        # Misc
        'dup': {'nargs': N(1), 'redfn': lambda i, v: [v[0], copy.copy(v[0])], 'checkfn': is_simple},
        'returnImm': {'nargs': N(2), 'redfn': BCReturn},
        # Useless
        'nop': {'nargs': N(0), 'redfn': lambda _1, _2: []},
        'startCommand': {'nargs': N(0), 'redfn': lambda _1, _2: []},
    }
    for details in inst_reductions.values():
        if 'checkfn' not in details:
            details['checkfn'] = lambda arg: isinstance(arg, BCValue)
    return inst_reductions

INST_REDUCTIONS = _inst_reductions()

def _bblock_reduce(bblock, literals):
    """
    For the given basic block, attempt to reduce all instructions to my higher
    level representations.
    """
    change = False
    loopchange = True
    while loopchange:
        loopchange = False

        for i, inst in enumerate(bblock.insts[:]):
            if not isinstance(inst, Inst): continue
            if inst.name in ('push1', 'push4'):
                bblock.insts[i] = BCLiteral(inst, literals[inst.ops[0][1]])
                loopchange = True
                break

            elif inst.name in INST_REDUCTIONS:
                IRED = INST_REDUCTIONS[inst.name]
                nargs = IRED['nargs'](inst)
                redfn = IRED['redfn']
                checkfn = IRED['checkfn']

                arglist = []
                argis = []
                for argi, arg in reversed(list(enumerate(bblock.insts[:i]))):
                    if len(arglist) == nargs:
                        break
                    if not isinstance(arg, BCValue):
                        break
                    if arg.stack() < 1:
                        continue
                    if not checkfn(arg):
                        break
                    arglist.append(arg)
                    argis.append(argi)
                arglist.reverse()
                if len(arglist) != nargs: continue
                newinsts = redfn(inst, arglist)
                if type(newinsts) is not list:
                    newinsts = [newinsts]
                bblock.insts[i:i+1] = newinsts
                # Remove any values we used as arguments.
                # Must go from biggest index to smallest! This happens
                # automatically because of the order we append in, but sort to
                # make it explicit
                for argi in sorted(argis, reverse=True):
                    bblock.insts.pop(argi)
                loopchange = True
                break

        if loopchange:
            change = True

    return change

def _get_jump(bblock):
    jump = bblock.insts[-1]
    return jump if isinstance(jump, BCJump) else None

def _bblock_flow(bblocks):
    # Recognise a basic if.
    # Observe that we don't try and recognise a basic if with no else branch -
    # it turns out that tcl implicitly inserts the else to provide all
    # execution branches with a value. TODO: this is an implementation detail
    # and should be handled more generically.
    # The overall structure consists of 4 basic blocks, arranged like so:
    # [if] -> [ifcode]  [elsecode] -> [end]
    #   |---------|----------^          ^        <- conditional jump to else
    #             |---------------------|        <- unconditional jump to end
    # We only care about the end block for checking that everything does end up
    # there. The other three blocks end up 'consumed' by a BCIf object.
    change = False
    loopchange = True
    while loopchange:
        loopchange = False

        for i in range(len(bblocks)):
            if len(bblocks[i:i+4]) < 4:
                continue
            jump0 = _get_jump(bblocks[i+0])
            jump1 = _get_jump(bblocks[i+1])
            jump2 = _get_jump(bblocks[i+2])
            if jump0 is None or jump0.on is None: continue
            if jump1 is None or jump1.on is not None: continue
            if jump2 is not None: continue
            if jump0.targetloc is not bblocks[i+2]: continue
            if jump1.targetloc is not bblocks[i+3]: continue
            if any([
                    isinstance(inst, Inst) for inst in
                    bblocks[i+1].insts + bblocks[i+2].insts
                    ]):
                continue
            targets = [target for target in [
                (lambda jump: jump and jump.targetloc)(_get_jump(src_bblock))
                for src_bblock in bblocks
            ] if target is not None]
            if targets.count(bblocks[i+1]) > 0: continue
            if targets.count(bblocks[i+2]) > 1: continue
            jumps = [bblocks[i+0].insts.pop(), bblocks[i+1].insts.pop()]
            assert jumps == [jump0, jump1]
            bblocks[i].insts.append(BCIf(jumps, bblocks[i+1:i+3]))
            bblocks[i+1:i+3] = []
            loopchange = True
            break

        if loopchange:
            change = True

    return change

def _bblock_join(bblocks):
    change = False
    loopchange = True
    while loopchange:
        loopchange = False

        for i in range(len(bblocks)):
            if len(bblocks[i:i+2]) < 2:
                continue
            bblock1, bblock2 = bblocks[i:i+2]
            if _get_jump(bblock1) is not None:
                continue
            targets = [target for target in [
                (lambda jump: jump and jump.targetloc)(_get_jump(src_bblock))
                for src_bblock in bblocks
            ] if target is not None]
            if bblock1 in targets or bblock2 in targets:
                continue
            bblock1.insts.extend(bblock2.insts)
            bblocks[i+1:i+2] = []
            loopchange = True
            break

        if loopchange:
            change = True

    return change

def decompile(bytecode, literals):
    """
    Given some bytecode and literals, attempt to decompile to tcl.
    """
    insts = getinsts(bytecode)
    bblocks = _bblock_create(insts)
    # Reduce bblock logic
    change = True
    while change:
        change = False
        change = any([_bblock_reduce(bblock, literals) for bblock in bblocks])
        change = change or _bblock_flow(bblocks)
        change = change or _bblock_join(bblocks)
    outstr = ''
    for bblock in bblocks:
        outstr += bblock.fmt()
        outstr += '\n'
    return outstr
