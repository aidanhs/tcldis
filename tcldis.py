from __future__ import print_function

import struct
import copy

import _tcldis
printbc = _tcldis.printbc
def getbc(*args, **kwargs):
    bytecode, bcliterals, bclocals = _tcldis.getbc(*args, **kwargs)
    return BC(bytecode, bcliterals, bclocals)
getbc.__doc__ = _tcldis.getbc.__doc__
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

class BC(object):
    def __init__(self, bytecode, bcliterals, bclocals):
        self._bytecode = bytecode
        self._literals = bcliterals
        self._locals = bclocals
        self._pc = 0
    def __len__(self):
        return len(self._bytecode) - self._pc
    def literal(self, n):
        return self._literals[n]
    def local(self, n):
        return self._locals[n]
    def peek1(self):
        return self._bytecode[self._pc]
    def pc(self):
        return self._pc
    def get(self, n):
        oldpc = self._pc
        self._pc += n
        return self._bytecode[oldpc:self._pc]
    def copy(self):
        bc = BC(self._bytecode, self._literals, self._locals)
        bc._pc = self._pc
        return bc

# Tcl bytecode instruction
class Inst(object):
    def __init__(self, bc, *args, **kwargs):
        super(Inst, self).__init__(*args, **kwargs)
        self.loc = bc.pc()
        bytecode = bc.get(INSTRUCTIONS[bc.peek1()]['num_bytes'])
        inst_type = INSTRUCTIONS[bytecode.pop(0)]
        self.name = inst_type['name']
        self.ops = []
        for opnum in inst_type['operands']:
            optype, getop = OPERANDS[opnum]
            if optype in ('INT1', 'INT4', 'UINT1', 'UINT4'):
                self.ops.append(getop(bytecode))
            elif optype in ('LVT1', 'LVT4'):
                self.ops.append(bc.local(getop(bytecode)))
            else:
                assert False
        # Note that this doesn't get printed on str() so we only see
        # the value when it gets reduced to a BCJump class
        if self.name in JUMP_INSTRUCTIONS:
            self.targetloc = self.loc + self.ops[0]

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
        assert type(self.value) is str
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

# This one is odd. inst.ops[0] is the index to the locals table, kv[0]
# is namespace::value, or value if looking at the same namespace (i.e.
# most of the time). For now we only handle the case where they're both
# the same, i.e. looking at the same namespace.
# Additionally, note there is a hack we apply before reducing to recognise
# that Tcl gives variable calls a return value.
class BCVariable(BCProcCall):
    def __init__(self, *args, **kwargs):
        super(BCVariable, self).__init__(*args, **kwargs)
        assert len(self.value) == 1
        assert self.value[0].fmt() == self.inst.ops[0]
    def __repr__(self):
        return 'BCVariable(%s)' % (self.value,)
    def fmt(self):
        cmd = 'variable %s' % (self.value[0].fmt(),)
        if self.stack():
            cmd = '[' + cmd + ']'
        return cmd

class BCReturn(BCValue):
    def __init__(self, *args, **kwargs):
        super(BCReturn, self).__init__(*args, **kwargs)
        assert len(self.value) == 2
        assert self.value[1].value == '' # Options
        assert self.inst.ops[0] == 0 # Code
        assert self.inst.ops[1] == 1 # Level
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

_destackable_bctypes = [BCProcCall, BCIf, BCReturn, BCVariable]

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

def getinsts(bc):
    """
    Given bytecode in a bytearray, return a list of Inst objects.
    """
    bc = bc.copy()
    insts = []
    while len(bc) > 0:
        insts.append(Inst(bc))
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
    firstop = lambda inst: inst.ops[0]
    def destack(v): v.stack(-1); return v
    def lit(s): return BCLiteral(None, s)
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

    def getargsgen(nargs_fn, checkargs_fn=None):
        def getargsfn(inst, bblock, i):
            nargs = nargs_fn(inst)
            arglist = []
            argis = []
            for argi, arg in reversed(list(enumerate(bblock.insts[:i]))):
                if len(arglist) == nargs:
                    break
                if not isinstance(arg, BCValue):
                    break
                if arg.stack() < 1:
                    continue
                if checkargs_fn and not checkargs_fn(arg):
                    break
                arglist.append(arg)
                argis.append(argi)
            arglist.reverse()
            if len(arglist) != nargs: return None
            # Remove any values we used as arguments.
            # Must go from biggest index to smallest! This happens
            # automatically because of the order we append in, but sort to
            # make it explicit
            for argi in sorted(argis, reverse=True):
                bblock.insts.pop(argi)
            return arglist
        return getargsfn

        # Expression operators
        #'gt': [N(2), BCExpr],

    # nargs, redfn, checkfn
    inst_reductions = {
        # Callers
        'invokeStk1': [[firstop], BCProcCall],
        'invokeStk4': [[firstop], BCProcCall],
        'listLength': [[N(1)], lambda inst, kv: BCProcCall(inst, [lit('llength'), kv[0]])],
        'incrStkImm': [[N(1)], lambda inst, kv: BCProcCall(inst, [lit('incr'), kv[0]] + ([lit(str(inst.ops[0]))] if inst.ops[0] != 1 else []))],
        'incrScalar1Imm': [[N(0)], lambda inst, kv: BCProcCall(inst, [lit('incr'), lit(inst.ops[0])] + ([lit(str(inst.ops[1]))] if inst.ops[1] != 1 else []))],
        'variable': [[N(1)], BCVariable],
        # Jumps
        'jump1': [[N(0)], lambda i, v: BCJump(None, i, v)],
        'jumpFalse1': [[N(1)], lambda i, v: BCJump(False, i, v)],
        'jumpTrue1': [[N(1)], lambda i, v: BCJump(True, i, v)],
        # Variable references
        'loadStk': [[N(1)], BCVarRef],
        'loadArrayStk': [[N(2)], BCArrayRef],
        'loadScalar1': [[N(0)], lambda inst, kv: BCVarRef(inst, [lit(inst.ops[0])])],
        'loadArray1': [[N(1)], lambda inst, kv: BCArrayRef(inst, [lit(inst.ops[0]), kv[0]])],
        # Variable sets
        'storeStk': [[N(2)], lambda inst, kv: BCProcCall(inst, [lit('set'), kv[0], kv[1]])],
        'storeArrayStk': [[N(3)], lambda inst, kv: BCProcCall(inst, [lit('set'), BCArrayElt(None, kv[:2]), kv[2]])],
        'storeScalarStk': [[N(2)], lambda inst, kv: BCProcCall(inst, [lit('set'), kv[0], kv[1]])],
        'storeScalar1': [[N(1)], lambda inst, kv: BCProcCall(inst, [lit('set'), lit(inst.ops[0]), kv[0]])],
        'storeArray1': [[N(2)], lambda inst, kv: BCProcCall(inst, [lit('set'), BCArrayElt(None, [lit(inst.ops[0]), kv[0]]), kv[1]])],
        # Value ignoring
        'done': [[N(1), can_destack], lambda i, v: destack(v[0])],
        'pop': [[N(1), can_destack], lambda i, v: destack(v[0])],
        # Misc
        'dup': [[N(1), is_simple], lambda i, v: [v[0], copy.copy(v[0])]],
        'returnImm': [[N(2)], BCReturn],
        # Useless
        'nop': [[N(0)], lambda _1, _2: []],
        'startCommand': [[N(0)], lambda _1, _2: []],
    }
    for inst, (getargsgen_args, redfn) in inst_reductions.items():
        inst_reductions[inst] = {
            'getargsfn': getargsgen(*getargsgen_args),
            'redfn': redfn,
        }
    return inst_reductions

INST_REDUCTIONS = _inst_reductions()

def _bblock_hack(bc, bblock):
    """
    The Tcl compiler has some annoying implementation details which must be
    recognised before any reduction.
    """
    # 'variable' does not push a result so the Tcl compiler inserts a push.
    variableis = []
    for i, inst in enumerate(bblock.insts):
        if not isinstance(inst, Inst): continue
        if not inst.name == 'variable': continue
        assert bblock.insts[i+1].name in ('push1', 'push4')
        assert bc.literal(bblock.insts[i+1].ops[0]) == ''
        variableis.append(i)
    [bblock.insts.pop(i+1) for i in reversed(variableis)]

def _bblock_reduce(bc, bblock):
    """
    For the given basic block, attempt to reduce all instructions to my higher
    level representations.
    """
    for i, inst in enumerate(bblock.insts):
        if not isinstance(inst, Inst): continue

        if inst.name in ('push1', 'push4'):
            bblock.insts[i] = BCLiteral(inst, bc.literal(inst.ops[0]))

        elif inst.name in INST_REDUCTIONS:
            IRED = INST_REDUCTIONS[inst.name]
            getargsfn = IRED['getargsfn']
            redfn = IRED['redfn']
            arglist = getargsfn(inst, bblock, i)
            if arglist is None: continue
            # args are popped so inst location changes
            i = i - len(arglist)
            newinsts = redfn(inst, arglist)
            if type(newinsts) is not list:
                newinsts = [newinsts]
            bblock.insts[i:i+1] = newinsts

        else:
            continue # No change, continue scanning basic blcok

        return True

    return False

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

        return True

    return False

def _bblock_join(bblocks):
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

        return True

    return False

def decompile(bc):
    """
    Given some bytecode and literals, attempt to decompile to tcl.
    """
    assert isinstance(bc, BC)
    insts = getinsts(bc)
    bblocks = _bblock_create(insts)
    # Reduce bblock logic
    [_bblock_hack(bc, bblock) for bblock in bblocks]
    change = True
    while change:
        change = False
        change = any([_bblock_reduce(bc, bblock) for bblock in bblocks])
        change = change or _bblock_flow(bblocks)
        change = change or _bblock_join(bblocks)
    outstr = ''
    for bblock in bblocks:
        outstr += bblock.fmt()
        outstr += '\n'
    return outstr
