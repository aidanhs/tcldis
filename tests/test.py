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

#cases.append(('list1', 'puts [list a b c]\n')) # **
cases.append(('list2', 'puts [list $a b c]\n')) # **

cases.append(('expr', 'puts [expr {$a > 1}]\n')) # **
cases.append(('catch', '''\
catch {my_bad_proc a b} msg
''')) # **

cases.append(('return', 'return 15\n')) # **
cases.append(('if', '''\
if {$a} {
\tputs a
}
''')) # **
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

# For bits of bytecode I can't reproduce from tcl, but need to be decompilable
class TestTclBC(unittest.TestCase):
    def assertTclEqual(self, case):
        bc, tcl = case
        self.assertEqual(tcl, tcldis.decompile(bc))

    def test_catch(self):
        self.assertTclEqual((
            tcldis.BC(
                bytearray(
                    b'E\x00\x00\x00\x00i\x00\x00\x00\x13\x00\x00\x00\x01\x01\x03' +
                    b'\x01\x04\n\x00\x06\x03\x11\x03\x11\x02\x03\x01\x05"\x07G' +
                    b'\x11\x02\x03HF@&\x19\x01\x06\x01\x07\x01\x08\x06\x03\x03i' +
                    b'\x00\x00\x00\x0c\x00\x00\x00\x01\x01\x01\x00"\x04\x01\x01\x03'
                ),
                ['','','name','run_me','-arg','0','someproc','-with-uplevel','$msg'],
                ['name','','msg','out'],
                []
            ),
            dedent('''\
                if {[catch {set out [run_me -arg $name]} msg]} {
                	someproc -with-uplevel {$msg}
                	return {}
                }
                '''
            )
        ))

def setupcase(test_class, name, case):
    setattr(
        test_class,
        'test_' + name,
        lambda self: self.assertTclEqual(case)
    )

for name, case in cases:
    setupcase(TestTclScript, name, case)
    if name not in ('array_set', 'foreach'):
        setupcase(TestTclProc, name, case)

if __name__ == '__main__':
    unittest.main()
