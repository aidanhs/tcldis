tcldis
======

This is a Python module to decompile Tcl bytecode, targeting Tcl 8.5 and
Python 2.6 - 2.7.

It is best used with reference to tclCompile.{c,h} from the Tcl source.

The extension is available under the 3-clause BSD license (see "LICENSE").

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
   - `returns: a human readable interpretation of the code when compiled`
   - `side effects: none`
 - `tcldis.getbc(tcl_code)`
   - `takes: string of valid tcl code`
   - `returns: byte array of compiled Tcl bytecode, list of literal values`
   - `side effects: none`

UNIX BUILD
----------

It is assumed that you
 - have got the repo (either by `git clone` or a tar.gz from the releases page).
 - have updated your package lists.

The build process fairly simple:
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
	% import tcldis
	% tcldis.printbc("set x 1")
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
