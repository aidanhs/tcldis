import tcldis
import unittest

from textwrap import dedent

class TestBasicTcl(unittest.TestCase):

    def assertTclEqual(self, tcl):
        self.assertEqual(tcl, tcldis.decompile(*tcldis.getbc(tcl)))

    def test_set(self):
        self.assertTclEqual('set x 15\n')

    def test_set_array(self):
        self.assertTclEqual('set x(a) 15\n')

    def test_ref(self):
        self.assertTclEqual('puts $a\n')

    def test_ref_array(self):
        self.assertTclEqual('puts $x(a)\n')

    # TODO: ensure compiles to more than just a proc call
    #def test_if(self):
    #    tcl = dedent(
    #        '''\
    #        if {$a} {
    #        \tputs a
    #        }
    #        '''
    #    )
    #    self.assertTclEqual(tcl)

    # TODO: ensure compiles to more than just a proc call
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

    # TODO: ensure compiles to more than just a proc call
    #def test_if_elseif(self):
    #    self.assertTclEqual(dedent(
    #        '''\
    #        if {$a} {
    #        \tputs a
    #        } elseif {$b} {
    #        \tputs b
    #        }
    #        '''
    #    ))

    # TODO: ensure compiles to more than just a proc call
    #def test_if_elseif_else(self):
    #    self.assertTclEqual(dedent(
    #        '''\
    #        if {$a} {
    #        \tputs a
    #        } elseif {$b} {
    #        \tputs b
    #        } else {
    #        \tputs c
    #        }
    #        '''
    #    ))

    # TODO: ensure compiles to more than just a proc call
    #def test_if_elseif_elseif_else(self):
    #    self.assertTclEqual(dedent(
    #        '''\
    #        if {$a} {
    #        \tputs a
    #        } elseif {$b} {
    #        \tputs b
    #        } elseif {$c} {
    #        \tputs c
    #        } else {
    #        \tputs d
    #        }
    #        '''
    #    ))

    # TODO: ensure compiles to more than just a proc call
    #def test_switch(self):
    #    self.assertTclEqual(dedent(
    #        '''\
    #        switch -exact $a {
    #            pat1 {
    #                puts my_body_1
    #            }
    #            pat2 {
    #                puts my_body_2
    #            }
    #            default {
    #                puts default
    #            }
    #        }
    #        '''
    #    ))

    # TODO: ensure compiles to more than just a proc call
    #def test_for(self):
    #    self.assertTclEqual(dedent(
    #        '''\
    #        for {set i 0} {$i < 5} {incr i} {
    #            puts $i
    #        }
    #        '''
    #    ))

    # TODO: ensure compiles to more than just a proc call
    # foreach
    # TODO: ensure compiles to more than just a proc call
    # dict for

    def test_array_set(self):
        self.assertTclEqual('array set x {a 1 b 2}\n')

    #def test_list(self):
    #    self.assertTclEqual('puts [list a b c]\n')

    def test_return(self):
        self.assertTclEqual('return 15\n')

if __name__ == '__main__':
    unittest.main()
