import tcldis
import unittest

from textwrap import dedent

class TestBasicTcl(unittest.TestCase):

    def assertTclEqual(self, tcl):
        self.assertEqual(tcl, tcldis.decompile(tcl))

    def test_set(self):
        tcl = 'set x 15\n'
        self.assertTclEqual(tcl)

    def test_set_array(self):
        tcl = 'set x(a) 15\n'
        self.assertTclEqual(tcl)

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
        tcl = dedent(
            '''\
            if {$a} {
            \tputs a
            } else {
            \tputs b
            }
            '''
        )
        self.assertTclEqual(tcl)

    def test_array_set(self):
        tcl = 'array set x {a 1 b 2}\n'
        self.assertTclEqual(tcl)

    #def test_list(self):
    #    tcl = 'puts [list a b c]'
    #    self.assertTclEqual(tcl)

if __name__ == '__main__':
    unittest.main()
