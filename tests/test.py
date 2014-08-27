import tclpy
import tcldis
import unittest

from textwrap import dedent

# TODO: ensure cases marked ** compile to more than just a proc call
cases = []
cases.append(('set', 'set x 15\n'))
cases.append(('set_array', 'set x(a) 15\n'))
cases.append(('array_set', 'array set x {a 1 b 2}\n')) # **
cases.append(('ref', 'puts $a\nputs $u::a\n'))
cases.append(('ref_array', 'puts $x(a)\n'))
cases.append(('incr', 'incr x\nincr x 5\n')) # **
cases.append(('variable', 'variable x\n')) # **

#cases.append(('list', 'puts [list a b c]\n')) # **

cases.append(('return', 'return 15\n')) # **
#cases.append(('if', '''\
#if {$a} {
#\tputs a
#}
#''')) # **
cases.append(('if_else', '''\
if {$a} {
\tputs a
} else {
\tputs b
}
''')) # **
#cases.append(('if_elseif', '''\
#if {$a} {
#\tputs a
#} elseif {$b} {
#\tputs b
#}
#''')) # **
#cases.append(('if_elseif_else', '''\
#if {$a} {
#\tputs a
#} elseif {$b} {
#\tputs b
#} else {
#\tputs c
#}
#''')) # **
#cases.append(('if_elseif_elseif_else', '''\
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
cases.append(('switch', '''\
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
#cases.append(('for', '''\
#for {set i 0} {$i < 5} {incr i} {
#\tputs $i
#}
#''')) # **
cases.append(('foreach', '''\
foreach {a b} {1 2 3 4} {
	puts $a
	puts $b
}
''')) # **

# TODO: dict for **
# TODO: expr **

class TestTclScript(unittest.TestCase):
    def assertTclEqual(self, tcl):
        self.assertEqual(tcl, tcldis.decompile(tcldis.getbc(tcl)))

class TestTclProc(unittest.TestCase):
    def assertTclEqual(self, tcl):
        proctcl = 'proc p {} {\n' + tcl + '\n}'
        tclpy.eval(proctcl)
        self.assertEqual(tcl, tcldis.decompile(tcldis.getbc(proc_name='p')))

def setupcase(test_class, name, case):
    setattr(
        test_class,
        'test_' + name,
        lambda self: self.assertTclEqual(case)
    )

for name, case in cases:
    setupcase(TestTclScript, name, case)
    if name in ('set', 'set_array', 'ref', 'ref_array', 'incr', 'variable'):
        setupcase(TestTclProc, name, case)

if __name__ == '__main__':
    unittest.main()
