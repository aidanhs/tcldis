set -e

TOP=$(pwd)
echo "echo -I $TOP/empython-build/python/Include -I $TOP/empython-build/python" > $TOP/python-config
chmod +x python-config
echo "TCL_INCLUDE_SPEC='-I $TOP/emtcl/tcl/generic -I $TOP/emtcl/tcl/unix'" > $TOP/tclConfig.sh

git clone --recursive https://github.com/aidanhs/empython.git empython-build
cd empython-build
    cd python && make -f ../Makefile prep em && cd ..
    cd ..

git clone --recursive https://github.com/aidanhs/emtcl.git
cd emtcl
    git submodule init && git submodule update
    make tclprep
    make emtcl.bc
    cd ..

git clone --recursive https://github.com/aidanhs/tcldis.git # don't use the tcl from here
cd tcldis
    sed -i 's/gcc/emcc/g' Makefile
    sed -i 's/TclDisassembleByteCodeObj/\0_/g' src/tcl_bcutil.c
    PATH=$TOP:$PATH make TCLCONFIG=$TOP/tclConfig.sh _tcldis.o
    emar rc lib_tcldis.a _tcldis.o
    cd opt/libtclpy
        sed -i 's/gcc/emcc/g' Makefile
        sed -i '/dlopen/d' generic/tclpy.c
        PATH=$TOP:$PATH make TCLCONFIG=$TOP/tclConfig.sh tclpy.o
        emar rc libtclpy.a tclpy.o
        cd ../..
    cd ..

rm -rf empython
git clone --recursive https://github.com/aidanhs/empython.git
cd empython
    ln -sf python/libpython2.7.a libpython.a
    cd python
        make -f ../Makefile prep
        make -f ../Makefile em
        echo 'tclpy -L../../tcldis/opt/libtclpy -ltclpy' >> Modules/Setup
        echo '_tcldis -L../../tcldis -l_tcldis' >> Modules/Setup
        emmake make || true
        cp ../python.native python && chmod +x python
        emmake make
    cd ..
    ln -s ../../../tcldis/tcldis.py python/Lib
    sed -i 's|libz\.a$|\0 ../tcldis/opt/libtclpy/libtclpy.a ../tcldis/lib_tcldis.a ../emtcl/emtcl.bc|' Makefile
    make
