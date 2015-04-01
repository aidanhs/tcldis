tcldis
======

This is a Python module to decompile Tcl bytecode, targeting Tcl 8.5 and
Python 2.6 - 2.7.

It is best used with reference to tclCompile.{c,h} from the Tcl source.

The extension is available under the 3-clause BSD license (see "LICENSE"),
apart from `src/tcl_bcutil.c`, which contains code taken directly from Tcl
and is available under the appropriate (BSD-style) license.

USAGE
-----

Reference:
 - `tcldis.inst_table()`
   - `takes: nothing`
   - `returns: a list of dicts describing Tcl bytecode instructions in the
      format described below:`
     - `{'stack_effect': 1, 'name': 'push1', 'operands': [3], 'num_bytes': 2}`
   - `side effects: none`
 - `tcldis.printbc(tcl_code)`
   - `takes: string of valid tcl code`
   - `returns: a human readable interpretation of Tcl bytecode`
   - `side effects: none`
 - `tcldis.getbc(tcl_code)` - see docstring
   - `takes: string of valid tcl code, a pointer to a Tcl_Obj or a proc name`
   - `returns: a BC object containing information about the bytecode`
   - `side effects: none`
 - `tcldis.decompile(bytecode)`
   - `takes: a BC object as returned by getbc`
   - `returns: string representing best-effort attempt at decompiling bytecode`
   - `side effects: none`
 - `tcldis.decompile_steps(bytecode)` - see docsting
   - `takes: a BC object as returned by getbc`
   - `returns: a list of steps and changes from the decompilation process`
   - `side effects: none`

UNIX BUILD
----------

It is assumed that you
 - have got the repo (either by `git clone` or a tar.gz from the releases page).
 - have updated your package lists.

The build process is fairly simple:
 - make sure `make` and `gcc` are installed.
 - make sure you can run `python-config` and have the Python headers available
   (usually installed by the Python development package for your distro).
 - locate the tclConfig.sh file and make sure you have the Tcl headers available
   (usually installed by the Tcl development package for your distro).
 - run `make`, specifying the tclConfig.sh path if not `/usr/lib/tclConfig.sh`.

On Ubuntu the default tclConfig.sh path is correct:

	$ sudo apt-get install -y python-dev tcl-dev
	$ cd tcldis
	$ make

For other distros you may need give the path of tclConfig.sh. E.g. CentOS 6.5:

	$ sudo yum install -y python-devel tcl-devel make gcc
	$ cd tcldis
	$ make TCLCONFIG=/usr/lib64/tclConfig.sh

Now try it out:

	$ python
	>>> import tcldis
	>>> tcldis.printbc("set x 1") # exactly the same as tcl::unsupported::disassemble
	ByteCode 0x0x26a0390, refCt 1, epoch 15, interp 0x0x26708f0 (epoch 15)
	  Source "set x 1"
	  Cmds 1, src 7, inst 6, litObjs 2, aux 0, stkDepth 2, code/src 0.00
	  Commands 1:
	      1: pc 0-4, src 0-6
	  Command 1: "set x 1"
	    (0) push1 0         # "x"
	    (2) push1 1         # "1"
	    (4) storeStk 
	    (5) done 
	>>> bc = tcldis.getbc('set x 1')
	>>> bc
	BC(bytearray(b'\x01\x00\x01\x01\x17\x00'),['x', '1'],[],[],0)
	>>> print bc
	Bytecode with 6 bytes of instructions, 2 literals, 0 locals, 0 auxs and pc 0
	>>> bc._literals
	['x', '1']


TESTS AND ACTUAL DECOMPILATION
------------------------------

The tests are a little more complex to set up as they require a build of
libtclpy with stubs disabled (tcldis itself cannot use stubs - it uses some Tcl
functions that aren't exposed by the stub library). Development is currently
done against a single tag of tcl (version 8.5.16) so tests will probably work
best against that version.

For convenience, libtclpy and the correct tag of tcl are available as git
submodules. You can get a self-contained (no system tcl required) working test
environment working like so:

    $ git submodule init
    $ git submodule update # takes a while to clone Tcl
    $ cd opt/tcl8.5/unix
    $ ./configure --prefix=$(pwd)/../../tcl_dist && make && make install
    $ cd ../../libtclpy
    $ make TCLCONFIG=$(pwd)/../tcl_dist/lib/tclConfig.sh TCL_STUBS=0
    $ cd ../..
    $ PYTHONPATH=opt/libtclpy make test

Now you can actually play with decompiling:

    $ PYTHONPATH=.:opt/libtclpy python
    >>> import tclpy
    >>> import tcldis
    >>> tclpy.eval('proc p {x} {if {$x > 5} {return 15}}')
    ''
    >>> bc = tcldis.getbc(proc_name='p')
    >>> print repr(bc)[:40]+'...' # internal representation
    BC(bytearray(b'\n\x00\x01\x000&\x10i\x00...
    >>> print tcldis.decompile(bc)
    if {$x > 5} {
            return 15
    }

