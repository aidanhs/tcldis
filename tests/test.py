import tclpy
import tcldis
import unittest

from textwrap import dedent

# TODO: ensure cases marked ** compile to more than just a proc call
cases = []
cases.append(('set', u'set x 15\n'))
cases.append(('set_array', u'set x(a) 15\n'))
cases.append(('array_set', u'array set x {a 1 b 2}\n')) # **
cases.append(('ref', u'puts $a\nputs $u::a\n'))
cases.append(('ref_array', u'puts $x(a)\n'))
cases.append(('incr', u'incr x\nincr x 5\n')) # **
cases.append(('variable', u'variable x\n')) # **
cases.append(('variable2', u'variable NS::x\n')) # **

#cases.append(('list1', 'puts [list a b c]\n')) # **
cases.append(('list2', u'puts [list $a b c]\n')) # **

cases.append(('expr', u'puts [expr {$a > 1}]\n')) # **
cases.append(('catch', u'''\
catch {my_bad_proc a b} msg
''')) # **

cases.append(('return', u'return 15\n')) # **
cases.append(('if', u'''\
if {$a} {
\tputs a
}
''')) # **
cases.append(('if_else', u'''\
if {$a} {
\tputs a
} else {
\tputs b
}
''')) # **
#cases.append(('if_elseif', u'''\
#if {$a} {
#\tputs a
#} elseif {$b} {
#\tputs b
#}
#''')) # **
#cases.append(('if_elseif_else', u'''\
#if {$a} {
#\tputs a
#} elseif {$b} {
#\tputs b
#} else {
#\tputs c
#}
#''')) # **
#cases.append(('if_elseif_elseif_else', u'''\
#if {$a} {
#\tputs a
#} elseif {$b} {
#\tputs b
#} elseif {$c} {
#\tputs c
#} else {
#\tputs d
#}
#''')) # **
cases.append(('switch', u'''\
switch -exact $a {
\tpat1 {
\t\tputs my_body_1
\t}
\tpat2 {
\t\tputs my_body_2
\t}
\tdefault {
\t\tputs default
\t}
}
''')) # **
#cases.append(('for', u'''\
#for {set i 0} {$i < 5} {incr i} {
#\tputs $i
#}
#''')) # **
cases.append(('foreach', u'''\
puts x
foreach {a b} {1 2 3 4} {
	puts $a
	puts $b
}
puts x
''')) # **

# TODO: dict for **
# TODO: expr **

cases.append(('if_nested_catch', u'''\
if {$a} {
\tif {[catch {xx $b} c]} {
\t\tputs b
\t}
\tputs x
} else {
\tputs c
}
''')) # **

# ----------

def checkDecompileStepStructure(self, steps, changes):

    self.assertIs(type(steps), list)
    self.assertGreater(len(steps), 0)
    prevSnapshot = None
    for snapshot in steps:
        if prevSnapshot is not None:
            self.assertNotEqual(prevSnapshot, snapshot)
        prevSnapshot = snapshot
        self.assertIs(type(snapshot), list)
        self.assertGreater(len(snapshot), 0)
        for bblock in snapshot:
            # Can have 0 length bblocks in an intermediary step
            self.assertIs(type(bblock), list)
            for line in bblock:
                self.assertIs(type(line), unicode)
                self.assertGreater(len(line), 0)

    self.assertIs(type(changes), list)
    # TODO: enable this when inter-bblock changes work
    #self.assertGreaterEqual(len(changes), len(steps)-1)
    self.assertGreater(len(changes), 0)
    for change in changes:
        self.assertIs(type(change), dict)
        self.assertItemsEqual(change.keys(), ['step', 'bblock', 'from', 'to'])
        self.assertIs(type(change['step']), int)
        self.assertIs(type(change['bblock']), int)
        ifrom = change['from']
        self.assertIs(type(ifrom), tuple)
        self.assertEqual(len(ifrom), 2)
        self.assertIs(type(ifrom[0]), int)
        self.assertIs(type(ifrom[1]), int)
        ito = change['to']
        self.assertIs(type(ito), tuple)
        self.assertEqual(len(ito), 2)
        self.assertIs(type(ito[0]), int)
        self.assertIs(type(ito[1]), int)

    # Check we have no 0 length bblocks in final result
    self.assertGreater(len(steps), 0)
    self.assertGreater(len(steps[-1]), 0) # snapshot
    for bblock in steps[-1]:
        self.assertGreater(len(bblock), 0)

# ----------

class TestTclScript(unittest.TestCase):
    def assertTclEqual(self, tcl):
        self.assertEqual(tcl, tcldis.decompile(tcldis.getbc(tcl)))
    def assertDecompileStepStructure(self, tcl):
        steps, changes = tcldis.decompile_steps(tcldis.getbc(tcl))
        checkDecompileStepStructure(self, steps, changes)

class TestTclProc(unittest.TestCase):
    def assertTclEqual(self, tcl):
        proctcl = 'proc p {} {\n' + tcl + '\n}'
        tclpy.eval(proctcl)
        self.assertEqual(tcl, tcldis.decompile(tcldis.getbc(proc_name='p')))
    def assertDecompileStepStructure(self, tcl):
        proctcl = 'proc p {} {\n' + tcl + '\n}'
        tclpy.eval(proctcl)
        steps, changes = tcldis.decompile_steps(tcldis.getbc(proc_name='p'))
        checkDecompileStepStructure(self, steps, changes)


def setupcase(test_class, name, case):
    setattr(
        test_class,
        'test_decompile_' + name,
        lambda self: self.assertTclEqual(case)
    )
    setattr(
        test_class,
        'test_decompilesteps_' + name,
        lambda self: self.assertDecompileStepStructure(case)
    )

for name, case in cases:
    setupcase(TestTclScript, name, case)
    if name != 'array_set':
        setupcase(TestTclProc, name, case)

if __name__ == '__main__':
    unittest.main()
