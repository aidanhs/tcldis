from __future__ import print_function

import struct
import itertools
from collections import namedtuple, OrderedDict

import _tcldis
printbc = _tcldis.printbc
def getbc(*args, **kwargs):
    bytecode, bcliterals, bclocals, bcauxs = _tcldis.getbc(*args, **kwargs)
    bcliterals = [bclit.decode('utf-8') for bclit in bcliterals]
    bclocals =   [bcloc.decode('utf-8') for bcloc in bclocals]
    return BC(bytecode, bcliterals, bclocals, bcauxs)
getbc.__doc__ = _tcldis.getbc.__doc__
literal_convert = _tcldis.literal_convert

INSTRUCTIONS = _tcldis.inst_table()
JUMP_INSTRUCTIONS = [
    'jump1', 'jump4', 'jumpTrue1', 'jumpTrue4', 'jumpFalse1', 'jumpFalse4'
]

TAG_BLOCK_JOIN = 'block_join'
TAG_BLOCK_RM   = 'block_rm'
TAG_FOREACH    = 'foreach'
TAG_CATCH      = 'catch'
TAG_IF         = 'if'
TAG_I_PUSH     = 'i_push'
TAG_I_OTHER    = 'i_other'
TAG_H_VARIABLE = 'h_variable'

def _getop(optype):
    """
    Given a C struct descriptor, return a function which will take the necessary
    bytes off the front of a bytearray and return the python value.
    """
    def getop_lambda(bc):
        # The 'standard' sizes in the struct module match up to what Tcl expects
        numbytes = struct.calcsize(optype)
        opbytes = ''.join([chr(bc.pop(0)) for _ in range(numbytes)])
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
    def __init__(self, bytecode, bcliterals, bclocals, bcauxs):
        self._bytecode = bytecode
        self._literals = bcliterals
        self._locals = bclocals
        self._auxs = bcauxs
        self._pc = 0
    def __repr__(self):
        return 'BC(%s,%s,%s,%s,%s)' % tuple([repr(v) for v in [
            self._bytecode,
            self._literals,
            self._locals,
            self._auxs,
            self._pc,
        ]])
    def __str__(self):
        fmtstr = (
            'Bytecode with %s bytes of instructions, %s literals, %s locals, ' +
            '%s auxs and pc %s'
        )
        return fmtstr % (
            len(self._bytecode),
            len(self._literals),
            len(self._locals),
            len(self._auxs),
            self._pc,
        )
    def __len__(self):
        return len(self._bytecode) - self._pc
    def literal(self, n):
        return self._literals[n]
    def local(self, n):
        return self._locals[n]
    def aux(self, n):
        return self._auxs[n]
    def peek1(self):
        return self._bytecode[self._pc]
    def pc(self):
        return self._pc
    def get(self, n):
        oldpc = self._pc
        self._pc += n
        return self._bytecode[oldpc:self._pc]
    def copy(self):
        bc = BC(self._bytecode, self._literals, self._locals, self._auxs)
        bc.get(self._pc)
        return bc

# Tcl bytecode instruction
InstTuple = namedtuple('InstTuple', ['loc', 'name', 'ops', 'targetloc'])
class Inst(InstTuple):
    def __new__(cls, bc):
        d = {}
        d['loc'] = bc.pc()
        bytecode = bc.get(INSTRUCTIONS[bc.peek1()]['num_bytes'])
        inst_type = INSTRUCTIONS[bytecode.pop(0)]
        d['name'] = inst_type['name']
        ops = []
        for opnum in inst_type['operands']:
            optype, getop = OPERANDS[opnum]
            if optype in ['INT1', 'INT4', 'UINT1', 'UINT4']:
                ops.append(getop(bytecode))
            elif optype in ['LVT1', 'LVT4']:
                ops.append(bc.local(getop(bytecode)))
            elif optype in ['AUX4']:
                ops.append(bc.aux(getop(bytecode)))
                auxtype, auxdata = ops[-1]
                if auxtype == 'ForeachInfo':
                    auxdata = [
                        [bc.local(varidx) for varidx in varlist]
                        for varlist in auxdata
                    ]
                else:
                    assert False
                ops[-1] = (auxtype, auxdata)
            else:
                assert False
        d['ops'] = tuple(ops)

        # Note that this doesn't get printed on str() so we only see
        # the value when it gets reduced to a BCJump class
        d['targetloc'] = None
        if d['name'] in JUMP_INSTRUCTIONS:
            d['targetloc'] = d['loc'] + d['ops'][0]

        return super(Inst, cls).__new__(cls, **d)

    def __init__(self, bc, *args, **kwargs):
        super(Inst, self).__init__(*args, **kwargs)

    def __str__(self):
        return '<%s: %s %s>' % (
            self.loc if self.loc is not None else '?',
            self.name,
            '(' + ', '.join([repr(o) for o in self.ops]) + ')',
        )

#################################################################
# My own representation of anything that can be used as a value #
#################################################################

# The below represent my interpretation of the Tcl stack machine

BCValueTuple = namedtuple('BCValueTuple', ['inst', 'value', 'stackn'])
class BCValue(BCValueTuple):
    def __new__(cls, inst, value):
        d = {}
        d['inst'] = inst
        if type(value) is list:
            assert all([v.stackn == 1 for v in value if isinstance(v, BCValue)])
            value = tuple(value)
        elif type(value) is unicode:
            pass
        else:
            assert False
        d['value'] = value
        d['stackn'] = 1
        return super(BCValue, cls).__new__(cls, **d)
    def __init__(self, inst, value, *args, **kwargs):
        super(BCValue, self).__init__(*args, **kwargs)
    def destack(self):
        assert self.stackn == 1
        return self._replace(stackn=self.stackn-1)
    def __repr__(self): assert False
    def fmt(self): assert False

class BCLiteral(BCValue):
    def __init__(self, *args, **kwargs):
        super(BCLiteral, self).__init__(*args, **kwargs)
        assert type(self.value) is unicode
    def __repr__(self):
        return 'BCLiteral(%s)' % (repr(self.value),)
    def fmt(self):
        val = self.value
        if val == '': return u'{}'
        if not any([c in val for c in '$[]{}""\f\r\n\t\v ']):
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
                .replace('$', '\\$')
            )
            val = u'"%s"' % (val,)
        else:
            val = u'{%s}' % (val,)
        return val

class BCVarRef(BCValue):
    def __init__(self, *args, **kwargs):
        super(BCVarRef, self).__init__(*args, **kwargs)
        assert len(self.value) == 1
    def __repr__(self):
        return 'BCVarRef(%s)' % (repr(self.value),)
    def fmt(self):
        return u'$' + self.value[0].fmt()

class BCArrayRef(BCValue):
    def __init__(self, *args, **kwargs):
        super(BCArrayRef, self).__init__(*args, **kwargs)
        assert len(self.value) == 2
    def __repr__(self):
        return 'BCArrayRef(%s)' % (repr(self.value),)
    def fmt(self):
        return u'$%s(%s)' % (self.value[0].fmt(), self.value[1].fmt())

class BCConcat(BCValue):
    def __init__(self, *args, **kwargs):
        super(BCConcat, self).__init__(*args, **kwargs)
        assert len(self.value) > 1
    def __repr__(self):
        return 'BCConcat(%s)' % (repr(self.value),)
    def fmt(self):
        # TODO: this won't always work, need to be careful of
        # literals following variables
        return u'"%s"' % (u''.join([v.fmt() for v in self.value]),)

class BCProcCall(BCValue):
    def __init__(self, *args, **kwargs):
        super(BCProcCall, self).__init__(*args, **kwargs)
        assert len(self.value) >= 1
    def __repr__(self):
        return 'BCProcCall(%s)' % (self.value,)
    def fmt(self):
        args = list(self.value)
        if args[0].fmt() == u'::tcl::array::set':
            args[0:1] = [BCLiteral(None, 'array'), BCLiteral(None, 'set')]
        cmd = u' '.join([arg.fmt() for arg in args])
        if self.stackn:
            cmd = u'[%s]' % (cmd,)
        return cmd

class BCSet(BCProcCall):
    def __init__(self, *args, **kwargs):
        super(BCSet, self).__init__(*args, **kwargs)
        assert len(self.value) == 2
    def __repr__(self):
        return 'BCSet(%s)' % (self.value,)
    def fmt(self):
        cmd = u'set %s %s' % tuple([v.fmt() for v in self.value])
        if self.stackn:
            cmd = u'[%s]' % (cmd,)
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
        # self.value[0].fmt() is the fully qualified name, if appropriate
        assert self.value[0].fmt().endswith(self.inst.ops[0])
    def __repr__(self):
        return 'BCVariable(%s)' % (self.value,)
    def fmt(self):
        cmd = u'variable %s' % (self.value[0].fmt(),)
        if self.stackn:
            cmd = u'[%s]' % (cmd,)
        return cmd

class BCExpr(BCValue):
    _exprmap = {
        'gt': (u'>', 2),
        'lt': (u'<', 2),
        'ge': (u'>=', 2),
        'le': (u'<=', 2),
        'eq': (u'==', 2),
        'neq': (u'!=', 2),
        'add': (u'+', 2),
        'not': (u'!', 1),
    }
    def __init__(self, *args, **kwargs):
        super(BCExpr, self).__init__(*args, **kwargs)
        _, nargs = self._exprmap[self.inst.name]
        assert len(self.value) == nargs
    def __repr__(self):
        return 'BCExpr(%s)' % (self.value,)
    def expr(self):
        op, nargs = self._exprmap[self.inst.name]
        if nargs == 1:
            expr = u'%s %s' % (op, self.value[0].fmt())
        elif nargs == 2:
            expr = u'%s %s %s' % (self.value[0].fmt(), op, self.value[1].fmt())
        return expr
    def fmt(self):
        return u'[expr {%s}]' % (self.expr(),)

class BCReturn(BCProcCall):
    def __init__(self, *args, **kwargs):
        super(BCReturn, self).__init__(*args, **kwargs)
        assert len(self.value) == 2
        assert self.value[1].value == '' # Options
        assert self.inst.ops[0] == 0 # Code
        assert self.inst.ops[1] == 1 # Level
    def __repr__(self):
        return 'BCReturn(%s)' % (repr(self.value),)
    def fmt(self):
        if self.value[0].value == '': return u'return'
        return u'return %s' % (self.value[0].fmt(),)

# TODO: I'm totally unsure about where this goes. tclCompile.c says it has a -1
# stack effect, which means it doesn't put anything back on the stack. But
# sometimes it's used instead of an actual return, which does put something on
# the stack (after consuming two items). The overall stack effect is the same,
# but the end value is different...
class BCDone(BCProcCall):
    def __init__(self, *args, **kwargs):
        super(BCDone, self).__init__(*args, **kwargs)
        # Unfortunately cannot be sure this is a BCProcCall as done is sometimes
        # used for the return call (i.e. tcl throws away the information that we've
        # written 'return'.
        assert len(self.value) == 1
    def __repr__(self):
        return 'BCDone(%s)' % (repr(self.value),)
    def fmt(self):
        # In the general case it's impossible to guess whether 'return' was written.
        if isinstance(self.value[0], BCProcCall):
            return self.value[0].destack().fmt()
        return u'return %s' % (self.value[0].fmt(),)

# self.value contains two bblocks, self.inst contains two jumps
class BCIf(BCProcCall):
    def __init__(self, *args, **kwargs):
        super(BCIf, self).__init__(*args, **kwargs)
        assert len(self.value) == len(self.inst) == 2
        assert all([isinstance(jump, BCJump) for jump in self.inst])
        assert self.inst[0].on in (True, False) and self.inst[1].on is None
    def __repr__(self):
        return 'BCIf(%s)' % (self.value,)
    def fmt(self):
        value = list(self.value)
        # An if condition takes 'ownership' of the values returned in any
        # of its branches
        for i, bblock in enumerate(self.value):
            inst = bblock.insts[-1]
            if isinstance(inst, BCLiteral):
                assert inst.value == ''
                value[i] = bblock.popinst()
            elif isinstance(inst, BCProcCall):
                value[i] = bblock.replaceinst(len(bblock.insts)-1, [inst.destack()])
            else:
                assert False

        if isinstance(self.inst[0].value[0], BCExpr):
            conditionstr = self.inst[0].value[0].expr()
            if self.inst[0].on is True:
                conditionstr = u'!(%s)' % (conditionstr,)
        else:
            conditionstr = self.inst[0].value[0].fmt()
            if self.inst[0].on is True:
                conditionstr = '!%s' % (conditionstr,)
        cmd = (
            u'if {%s} {\n\t%s\n}' % (conditionstr, value[0].fmt().replace('\n', '\n\t'))
        )
        if len(value[1].insts) > 0:
            cmd += (
                u' else {\n\t%s\n}' % (value[1].fmt().replace('\n', '\n\t'),)
            )
        if self.stackn:
            cmd = u'[%s]' % (cmd,)
        return cmd

class BCCatch(BCProcCall):
    def __init__(self, *args, **kwargs):
        super(BCCatch, self).__init__(*args, **kwargs)
        assert len(self.value) == 3
        assert all([isinstance(v, BBlock) for v in self.value])
        begin, middle, end = self.value
        # Make sure we recognise the overall structure of this catch
        assert (all([
            len(begin.insts) >= 4, # beginCatch4, code, return code, jump
            len(middle.insts) == 2,
            len(end.insts) == 4,
        ]) and all([
            isinstance(begin.insts[-3], BCProcCall),
            isinstance(begin.insts[-2], BCLiteral),
            isinstance(begin.insts[-1], BCJump),
        ]) and all([
            middle.insts[0].name == 'pushResult',
            middle.insts[1].name == 'pushReturnCode',
            end.insts[0].name    == 'endCatch',
            end.insts[1].name    == 'reverse', end.insts[1].ops[0] == 2,
            end.insts[2].name    == 'storeScalar1',
            end.insts[3].name    == 'pop',
        ]))
    def __repr__(self):
        return 'BCCatch(%s)' % (self.value,)
    def fmt(self):
        begin, _, end = self.value
        # Nail down the details and move things around to our liking
        begin = begin.replaceinst((-3, -2), [begin.insts[-3].destack()])
        begin = begin.popinst().popinst().replaceinst(0, [])
        catchblock = begin.fmt()
        varname = end.insts[2].ops[0]
        cmd = u'catch {%s} %s' % (catchblock, varname)
        if self.stackn:
            cmd = u'[%s]' % (cmd,)
        return cmd

class BCForeach(BCProcCall):
    def __init__(self, *args, **kwargs):
        super(BCForeach, self).__init__(*args, **kwargs)
        assert len(self.value) == 4
        assert all([isinstance(v, BBlock) for v in self.value[:3]])
        begin, step, code, lit = self.value
        # Make sure we recognise the overall structure of foreach
        assert (all([
            len(begin.insts) == 2, # list temp var, foreach start
            len(step.insts) == 2, # foreach step, jumpfalse
            len(code.insts) > 1,
        ]) and all([
            isinstance(begin.insts[0], BCSet),
            isinstance(begin.insts[1], Inst),
            isinstance(step.insts[0], Inst),
            isinstance(step.insts[1], Inst),
            isinstance(code.insts[-1], BCJump),
            isinstance(lit, BCLiteral),
        ]) and all([
            begin.insts[1].name == 'foreach_start4',
            step.insts[0].name == 'foreach_step4',
            step.insts[1].name == 'jumpFalse1',
        ]))
        # Nail down the details and move things around to our liking
        assert begin.insts[1].ops[0] == step.insts[0].ops[0]
        assert len(begin.insts[1].ops[0][1]) == 1
    def __repr__(self):
        return 'BCForeach(%s)' % (self.value,)
    def fmt(self):
        value = list(self.value)
        value[2] = value[2].popinst()
        # TODO: this is lazy
        fevars = ' '.join(value[0].insts[1].ops[0][1][0])
        felist = value[0].insts[0].value[1].fmt()
        feblock = '\n\t' + value[2].fmt().replace('\n', '\n\t') + '\n'
        cmd = u'foreach {%s} %s {%s}' % (fevars, felist, feblock)
        if self.stackn:
            cmd = u'[%s]' % (cmd,)
        return cmd

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
        return unicode(self)

# Just a formatting container for the form a(x)
class BCArrayElt(BCNonValue):
    def __init__(self, *args, **kwargs):
        super(BCArrayElt, self).__init__(*args, **kwargs)
        assert len(self.value) == 2
    def __repr__(self):
        return 'BCArrayElt(%s)' % (repr(self.value),)
    def fmt(self):
        return u'%s(%s)' % (self.value[0].fmt(), self.value[1].fmt())

##############################
# Any basic block structures #
##############################

# Basic block, containing a linear flow of logic
class BBlock(object):
    def __init__(self, insts, loc, *args, **kwargs):
        super(BBlock, self).__init__(*args, **kwargs)
        assert type(insts) is list
        assert type(loc) is int
        self.insts = tuple(insts)
        self.loc = loc
    def __repr__(self):
        return 'BBlock(at %s, %s insts)' % (self.loc, len(self.insts))
    def replaceinst(self, ij, replaceinsts):
        newinsts = list(self.insts)
        if type(ij) is not tuple:
            assert ij >= 0
            ij = (ij, ij+1)
        assert type(replaceinsts) is list
        newinsts[ij[0]:ij[1]] = replaceinsts
        return BBlock(newinsts, self.loc)
    def appendinsts(self, insts):
        return self.replaceinst((len(self.insts), len(self.insts)), insts)
    def popinst(self):
        return self.replaceinst(len(self.insts)-1, [])
    def fmt_insts(self):
        fmt_list = []
        for inst in self.insts:
            if isinstance(inst, Inst):
                fmt_str = unicode(inst)
            elif (isinstance(inst, BCValue) and not isinstance(inst, BCDone) and
                    inst.stackn == 1):
                # BCDone is an odd one - it leaves something on the stack.
                # That's ok, it's usually because we've compiled a proc body
                # and the stack value is the return value - so we don't want to
                # display a stack indicator, but we do want to leave stackn as 1
                # for programmatic inspection.
                # >> symbol
                fmt_str = u'\u00bb %s' % (inst.fmt(),)
            else:
                fmt_str = inst.fmt()
            fmt_list.append(fmt_str)
        return fmt_list
    def fmt(self):
        return u'\n'.join(self.fmt_insts())

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
        if inst.targetloc is not None:
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
        elif inst.name in ['beginCatch4', 'endCatch']:
            starts.add(inst.loc)
            if inst.loc != 0:
                ends.add(insts[i-1].loc)
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
    return bblocks

def _inst_reductions():
    """
    Define how each instruction is reduced to one of my higher level
    representations.
    """
    def N(n): return lambda _: n
    firstop = lambda inst: inst.ops[0]
    def lit(s): return BCLiteral(None, s)
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
                if arg.stackn < 1:
                    continue
                if checkargs_fn and not checkargs_fn(arg):
                    break
                arglist.append(arg)
                argis.append(argi)
            arglist.reverse()
            if len(arglist) != nargs: return None
            return arglist
        return getargsfn

    # nargs, redfn, checkfn
    inst_reductions = {
        # Callers
        'invokeStk1': [[firstop], BCProcCall],
        'invokeStk4': [[firstop], BCProcCall],
        'list':[[firstop], lambda inst, kv: BCProcCall(inst, [lit(u'list')] + kv)],
        'listLength': [[N(1)], lambda inst, kv: BCProcCall(inst, [lit(u'llength'), kv[0]])],
        'incrStkImm': [[N(1)], lambda inst, kv: BCProcCall(inst, [lit(u'incr'), kv[0]] + ([lit(unicode(inst.ops[0]))] if inst.ops[0] != 1 else []))],
        'incrScalar1Imm': [[N(0)], lambda inst, kv: BCProcCall(inst, [lit(u'incr'), lit(inst.ops[0])] + ([lit(unicode(inst.ops[1]))] if inst.ops[1] != 1 else []))],
        'incrScalarStkImm': [[N(1)], lambda inst, kv: BCProcCall(inst, [lit(u'incr'), kv[0]] + ([lit(unicode(inst.ops[0]))] if inst.ops[0] != 1 else []))],
        'variable': [[N(1)], BCVariable],
        # Jumps
        'jump1': [[N(0)], lambda i, v: BCJump(None, i, v)],
        'jumpFalse1': [[N(1)], lambda i, v: BCJump(False, i, v)],
        'jumpTrue1': [[N(1)], lambda i, v: BCJump(True, i, v)],
        # Variable references
        'loadStk': [[N(1)], BCVarRef],
        'loadScalarStk': [[N(1)], BCVarRef],
        'loadArrayStk': [[N(2)], BCArrayRef],
        'loadScalar1': [[N(0)], lambda inst, kv: BCVarRef(inst, [lit(inst.ops[0])])],
        'loadArray1': [[N(1)], lambda inst, kv: BCArrayRef(inst, [lit(inst.ops[0]), kv[0]])],
        # Variable sets
        'storeStk': [[N(2)], BCSet],
        'storeScalarStk': [[N(2)], BCSet],
        'storeArrayStk': [[N(3)], lambda inst, kv: BCSet(inst, [BCArrayElt(None, kv[:2]), kv[2]])],
        'storeScalar1': [[N(1)], lambda inst, kv: BCSet(inst, [lit(inst.ops[0]), kv[0]])],
        'storeArray1': [[N(2)], lambda inst, kv: BCSet(inst, [BCArrayElt(None, [lit(inst.ops[0]), kv[0]]), kv[1]])],
        # Expressions
        'gt': [[N(2)], BCExpr],
        'lt': [[N(2)], BCExpr],
        'ge': [[N(2)], BCExpr],
        'le': [[N(2)], BCExpr],
        'eq': [[N(2)], BCExpr],
        'neq': [[N(2)], BCExpr],
        'add': [[N(2)], BCExpr],
        'not': [[N(1)], BCExpr],
        # Misc
        'concat1': [[firstop], BCConcat],
        'pop': [[N(1), lambda arg: isinstance(arg, BCProcCall)], lambda i, v: v[0].destack()],
        'dup': [[N(1), is_simple], lambda i, v: [v[0], v[0]]],
        'done': [[N(1)], BCDone],
        'returnImm': [[N(2)], BCReturn],
        # Useless
        'tryCvtToNumeric': [[N(0)], lambda _1, _2: []], # Theoretically does something...
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
    changes = []
    for i, inst in enumerate(bblock.insts):
        if not isinstance(inst, Inst): continue
        if not inst.name == 'variable': continue
        assert bblock.insts[i+1].name in ['push1', 'push4']
        assert bc.literal(bblock.insts[i+1].ops[0]) == ''
        variableis.append(i)
    for i in reversed(variableis):
        bblock = bblock.replaceinst(i+1, [])
        changes.append((TAG_H_VARIABLE, (i+1, i+2), (i+1, i+1)))
    return bblock, changes

def _bblock_reduce(bc, bblock):
    """
    For the given basic block, attempt to reduce all instructions to my higher
    level representations.
    """
    changes = []
    for i, inst in enumerate(bblock.insts):
        if not isinstance(inst, Inst): continue

        if inst.name in ['push1', 'push4']:
            bblock = bblock.replaceinst(i, [BCLiteral(inst, bc.literal(inst.ops[0]))])
            changes.append((TAG_I_PUSH, (i, i+1), (i, i+1)))

        elif inst.name in INST_REDUCTIONS:
            IRED = INST_REDUCTIONS[inst.name]
            getargsfn = IRED['getargsfn']
            redfn = IRED['redfn']
            arglist = getargsfn(inst, bblock, i)
            if arglist is None: continue
            newinsts = redfn(inst, arglist)
            if type(newinsts) is not list:
                newinsts = [newinsts]
            irange = (i-len(arglist), i+1)
            bblock = bblock.replaceinst(irange, newinsts)
            changes.append((TAG_I_OTHER, irange, (irange[0], irange[0]+len(newinsts))))

        else:
            continue # No change, continue scanning basic blcok

        break

    return bblock, changes

def _get_targets(bblocks):
    targets = [target for target in [
        (lambda jump: jump and jump.targetloc)(_get_jump(src_bblock))
        for src_bblock in bblocks
    ] if target is not None]
    inst_targets = [bblock.insts for bblock in bblocks]
    inst_targets = [i for i in itertools.chain(*inst_targets)]
    inst_targets = [i for i in inst_targets if isinstance(i, Inst)]
    inst_targets = [i.targetloc for i in inst_targets if i.targetloc is not None]
    return targets + inst_targets
def _get_jump(bblock):
    if len(bblock.insts) == 0: return None
    jump = bblock.insts[-1]
    if not isinstance(jump, BCJump): return None
    return jump
def _is_catch_begin(bblock):
    if len(bblock.insts) == 0: return False
    catch = bblock.insts[0]
    if not isinstance(catch, Inst): return False
    return catch.name == 'beginCatch4'
def _is_catch_end(bblock):
    if len(bblock.insts) == 0: return False
    catch = bblock.insts[0]
    if not isinstance(catch, Inst): return False
    return catch.name == 'endCatch'

def _bblock_flow(bblocks):
    # Recognise a basic if.
    # Observe that we don't try and recognise a basic if with no else branch -
    # it turns out that tcl implicitly inserts the else to provide all
    # execution branches with a value. TODO: this is an implementation detail
    # and should be handled more generically.
    # The overall structure consists of 4 basic blocks, arranged like so:
    # [if] -> [ifcode]  [elsecode] -> [unrelated code after if]
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
        if jump0.targetloc != bblocks[i+2].loc: continue
        if jump1.targetloc != bblocks[i+3].loc: continue
        if any([
                isinstance(inst, Inst) for inst in
                bblocks[i+1].insts + bblocks[i+2].insts
                ]):
            continue
        targets = _get_targets(bblocks)
        if targets.count(bblocks[i+1].loc) > 0: continue
        if targets.count(bblocks[i+2].loc) > 1: continue
        # Looks like an 'if', apply the bblock transformation
        changestart = ((i, 0), (i+2, len(bblocks[i+2].insts)))
        jumps = [bblocks[i+0].insts[-1], bblocks[i+1].insts[-1]]
        bblocks[i+0] = bblocks[i+0].popinst()
        bblocks[i+1] = bblocks[i+1].popinst()
        assert jumps == [jump0, jump1]
        bblocks[i] = bblocks[i].appendinsts([BCIf(jumps, bblocks[i+1:i+3])])
        bblocks[i+1:i+3] = []
        changeend = ((i, 0), (i, len(bblocks[i].insts)))
        return [(TAG_IF, changestart, changeend)]

    # Recognise a catch
    # The overall structure consists of 3 basic blocks, arranged like so:
    # [beginCatch+code]   [oncatch]   [endCatch+unrelated code after catch]
    #        |----------------------------^    <- unconditional jump to endCatch
    # The oncatch block is a series of instructions for handling when the code
    # throws an exception - note there is no direct execution path to them. We
    # make a number of assertions about them in case the bytecode compiler ever
    # does something unexpected with them. All blocks are 'consumed' and replaced
    # with a single BCCatch.
    # TODO: because we steal instructions from the endCatch block, the bblock 'loc'
    # is no longer correct!
    for i in range(len(bblocks)):
        if len(bblocks[i:i+3]) < 3:
            continue
        begin = bblocks[i+0]
        middle = bblocks[i+1]
        end = bblocks[i+2]
        if not _is_catch_begin(begin): continue
        if not _is_catch_end(end): continue
        assert not (_is_catch_end(begin) or _is_catch_begin(end))
        assert not (_is_catch_end(middle) or _is_catch_begin(middle))
        if any([isinstance(inst, Inst) for inst in begin.insts[1:]]):
            continue
        # Looks like a 'catch', apply the bblock transformation
        changestart = ((i, 0), (i+2, 4))
        endcatchinst = end.insts[0]
        end = end.replaceinst(0, [])
        endcatch = BBlock([endcatchinst], endcatchinst.loc)
        if (len(end.insts) > 2 and
                isinstance(end.insts[0], Inst) and
                isinstance(end.insts[1], Inst) and
                isinstance(end.insts[2], Inst) and
                end.insts[0].name == 'reverse' and
                end.insts[1].name == 'storeScalar1' and
                end.insts[2].name == 'pop'
            ):
            endcatch = endcatch.appendinsts(list(end.insts[0:3]))
            end = end.replaceinst((0, 3), [])
        else:
            assert False
        bccatch = BCCatch(None, [begin, middle, endcatch])
        bblocks[i] = begin.replaceinst((0, len(begin.insts)), [bccatch])
        bblocks[i+2] = end
        bblocks[i+1:i+2] = []
        changeend = ((i, 0), (i, len(bblocks[i].insts)))
        return [(TAG_CATCH, changestart, changeend)]

    # Recognise a foreach.
    # The overall structure consists of 4 basic blocks, arranged like so:
    # [unrelated code+fe start] -> [fe step]  [fe code] -> [unrelated code to fe]
    #                        ^  |--------|-----------^   <- conditional jump to end
    #                        |-----------|               <- unconditional jump to fe step
    # We only care about the end block for checking that everything does end up
    # there. The other three blocks end up 'consumed' by a BCForEach object.
    # If possible, we try and consume the BCLiteral sitting in the first instruction of
    # end, though it may already have been consumed by a return call.
    for i in range(len(bblocks)):
        if len(bblocks[i:i+4]) < 4:
            continue
        jump0 = _get_jump(bblocks[i+0])
        jump1 = bblocks[i+1].insts[-1]
        jump2 = _get_jump(bblocks[i+2])
        if jump0 is not None: continue
        # Unreduced because jumps don't know how to consume foreach_step
        if not isinstance(jump1, Inst) or jump1.name != 'jumpFalse1': continue
        if jump2 is None or jump2.on is not None: continue
        if jump1.targetloc is not bblocks[i+3].loc: continue
        if jump2.targetloc is not bblocks[i+1].loc: continue
        if any([isinstance(inst, Inst) for inst in bblocks[i+2].insts]): continue
        if not isinstance(bblocks[i+3].insts[0], BCLiteral): continue
        targets = _get_targets(bblocks)
        if targets.count(bblocks[i+1].loc) > 1: continue
        if targets.count(bblocks[i+2].loc) > 0: continue
        if targets.count(bblocks[i+3].loc) > 1: continue
        # Looks like a 'foreach', apply the bblock transformation
        changestart = ((i, len(bblocks[i].insts)-1), (i+3, 1))
        foreach_start = bblocks[i].insts[-1]
        bblocks[i] = bblocks[i].popinst()
        numvarlists = len(foreach_start.ops[0][1])
        varlists = []
        for i in range(numvarlists):
            varlists.append(bblocks[i].insts[-1])
            bblocks[i] = bblocks[i].popinst()
        # TODO: Location isn't actually correct...do we care?
        begin = BBlock(varlists + [foreach_start], foreach_start.loc)
        end = bblocks[i+3].insts[0]
        bblocks[i+3] = bblocks[i+3].replaceinst(0, [])
        foreach = BCForeach(None, [begin] + bblocks[i+1:i+3] + [end])
        bblocks[i] = bblocks[i].appendinsts([foreach])
        bblocks[i+1:i+3] = []
        changeend = ((i, len(bblocks[i].insts)-1), (i, len(bblocks[i].insts)))
        return [(TAG_FOREACH, changestart, changeend)]

    return []

def _bblock_join(bblocks):

    # Remove empty unused blocks
    # TODO: unknown if this is needed
    for i, bblock in enumerate(bblocks):
        if len(bblock.insts) > 0: continue
        targets = _get_targets(bblocks)
        if bblock.loc in targets: continue
        bblocks[i:i+1] = []

        previ = 0 if i == 0 else i-1
        previlen = len(bblocks[previ].insts)
        return [(TAG_BLOCK_RM, ((i, 0), (i, 0)), ((previ, previlen), (previ, previlen)))]

    # Join together blocks if possible
    for i in range(len(bblocks)):
        if len(bblocks[i:i+2]) < 2:
            continue
        bblock1, bblock2 = bblocks[i:i+2]
        targets = _get_targets(bblocks)
        # If the end of bblock1 or the beginning of bblock2 should remain as
        # bblock boundaries, do not join them.
        if _get_jump(bblock1) is not None:
            continue
        # Unreduced jumps
        if any([isinstance(inst, Inst) and inst.targetloc is not None
                for inst in bblock1.insts[-1:]]):
            continue
        if bblock2.loc in targets:
            continue
        if _is_catch_begin(bblock2):
            continue
        if _is_catch_end(bblock2):
            continue
        changestart = ((i, 0), (i+1, len(bblocks[i+1].insts)))
        bblocks[i] = bblock1.appendinsts(list(bblock2.insts))
        bblocks[i+1:i+2] = []
        changeend = ((i, 0), (i, len(bblocks[i].insts)))
        return [(TAG_BLOCK_JOIN, changestart, changeend)]

    return False

def _bblocks_operation(bblock_op, bc, bblocks):
    """
    Take a per-bblock operation and wrap it to add the correct location information
    indicating the ith bblock. Returns a list of bblocks and a flat list of changes.
    """
    operbblocks = []
    operchanges = []
    operlist = [bblock_op(bc, bblock) for bblock in bblocks]
    for bbi, (operbblock, bblockchanges) in enumerate(operlist):
        operbblocks.append(operbblock)
        operchanges.extend([
            (tag, ((bbi, lfrom1), (bbi, lfrom2)), ((bbi, lto1), (bbi, lto2)))
            for tag, (lfrom1, lfrom2), (lto1, lto2) in bblockchanges
        ])
    return operbblocks, operchanges

def _decompile(bc):
    """
    Given some bytecode and literals, attempt to decompile to tcl.
    """
    assert isinstance(bc, BC)
    insts = getinsts(bc)
    bblocks = _bblock_create(insts)
    yield bblocks[:], []

    # Reduce bblock logic
    hackedbblocks, changes = _bblocks_operation(_bblock_hack, bc, bblocks)
    if changes:
        bblocks = hackedbblocks
        yield bblocks[:], changes

    changes = True
    while changes:
        changes = []
        if not changes:
            bblocks, changes = _bblocks_operation(_bblock_reduce, bc, bblocks)
        if not changes:
            changes = _bblock_join(bblocks)
        if not changes:
            changes = _bblock_flow(bblocks)
        if changes: yield bblocks[:], changes

def _bblocks_fmt(bblocks):
    outstr = ''
    for bblock in bblocks:
        #outstr += '===========%s\n' % (bblock)
        outstr += bblock.fmt()
        outstr += '\n'
    return outstr

def decompile(bc):
    bblocks = None
    for bblocks, _ in _decompile(bc):
        pass
    return _bblocks_fmt(bblocks)

def decompile_steps(bc):
    """
    Given some bytecode, returns a tuple of `(steps, changes)` for decompilation.

    `steps` is a list of 'snapshot's of each stage of the decompilation.
    Each 'snapshot' is a list of 'basic block's in the program in that snapshot.
    Each 'basic block' is a list of 'line's in that bblock.
    Each 'line' is a string. The definition of a line is flexible - it might be
    a call to `foreach` (with all nested instructions), it might be a single
    bytecode instruction.
    In summary, `steps` is a list of lists of lists of strings.

    `changes` is a list of 'change descriptor's.
    Each change descriptor looks like
    {
        'step': si,
        'from': ((bbfrom1, lfrom1), (bbfrom2, lfrom2)),
        'to':   ((bbto1, lto1), (bbto2, lto2)),
        'tag':  tag,
    }
     - si      is the index of the step this change applies to
     - bbfrom1 is the index of the start block of the source changed lines
     - lfrom1  is the slice index of the start of the source changed lines
     - bbfrom2 is the index of the end block of the source changed lines
     - lfrom2  is the slice index of the end of the source changed lines
     - bbto1   is the index of the start block of the target changed lines
     - lto1    is the slice index of the start of the target changed lines
     - bbto2   is the index of the start block of the source changed lines
     - lto2    is the slice index of the end of the target change lines
     - tag     is some string identifier of the type of change made
    Note that these are *slice* indexes, i.e. like python. So if lto1 and lto2
    are the same, it means the source lines have been reduced to a line of
    width 0 (i.e. have been removed entirely).
    """
    steps = []
    changes = []
    for si, (sbblocks, schanges) in enumerate(_decompile(bc)):
        step = []
        for sbblock in sbblocks:
            step.append(sbblock.fmt_insts())
        for schange in schanges:
            tag, lfrom, lto = schange
            changes.append({
                'step': si-1,
                'from': lfrom,
                'to': lto,
                'tag': tag,
            })
        steps.append(step)
    return steps, changes
