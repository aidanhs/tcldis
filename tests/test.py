import tcldis
import unittest

from textwrap import dedent

class TestBasicTcl(unittest.TestCase):

    def assertTclEqual(self, tcl):
        self.assertEqual(tcl, tcldis.decompile(tcl))

    def test_set(self):
        self.assertTclEqual('set x 15\n')

    def test_set_array(self):
        self.assertTclEqual('set x(a) 15\n')

    def test_ref(self):
        self.assertTclEqual('puts $a\n')

    def test_ref_array(self):
        self.assertTclEqual('puts $x(a)\n')

    #def test_if(self):
    #    tcl = dedent(
    #        '''\
    #        if {$a} {
    #        \tputs a
    #        }
    #        '''
    #    )
    #    self.assertTclEqual(tcl)

    def test_if_else(self):
        self.assertTclEqual(dedent(
            '''\
            if {$a} {
            \tputs a
            } else {
            \tputs b
            }
            '''
        ))

    def test_array_set(self):
        self.assertTclEqual('array set x {a 1 b 2}\n')

    #def test_list(self):
    #    tcl = 'puts [list a b c]'
    #    self.assertTclEqual(tcl)

if __name__ == '__main__':
    unittest.main()
