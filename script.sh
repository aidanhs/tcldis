set -e

[ -f "$(which emcc)" ] || (echo "emcc not found" && exit 1)

TOP=$(pwd)
echo "echo -I $TOP/empython-build/python/Include -I $TOP/empython-build/python" > $TOP/python-config
chmod +x python-config
echo "TCL_INCLUDE_SPEC='-I $TOP/emtcl/tcl/generic -I $TOP/emtcl/tcl/unix'" > $TOP/tclConfig.sh

git clone --recursive https://github.com/aidanhs/empython.git empython-build
cd empython-build/python
    make -f ../Makefile prep
    make -f ../Makefile em
    cd ../..

git clone --recursive https://github.com/aidanhs/tcldis.git
cp tcldis/web/react-0.12.2.min.js .
cp tcldis/web/style.css .

git clone --recursive https://github.com/aidanhs/emtcl.git

cd emtcl
    # make emtcl compile the optimal tcl version for tcldis
    cd tcl
        git checkout $(cd ../../tcldis/opt/tcl8.5 && git rev-parse HEAD)
        cd ..
    make tclprep
    make emtcl.bc
    cd ..

cd tcldis
    sed -i 's/gcc/emcc/g' Makefile
    sed -i 's/TclDisassembleByteCodeObj/\0_/g' src/tcl_bcutil.c
    sed -i 's/-O2/-Oz/g' Makefile
    PATH=$TOP:$PATH make TCLCONFIG=$TOP/tclConfig.sh _tcldis.o
    emar rc lib_tcldis.a _tcldis.o
    cd opt/libtclpy
        sed -i 's/gcc/emcc/g' Makefile
        sed -i '/dlopen/d' generic/tclpy.c
        sed -i 's/-O2/-Oz/g' Makefile
        PATH=$TOP:$PATH make TCLCONFIG=$TOP/tclConfig.sh tclpy.o
        emar rc libtclpy.a tclpy.o
        cd ../..
    cd ..

git clone --recursive https://github.com/aidanhs/empython.git
cd empython
    ln -sf python/libpython2.7.a libpython.a
    cd python
        make -f ../Makefile prep
        make -f ../Makefile em
        echo 'tclpy -L../../tcldis/opt/libtclpy -ltclpy' >> Modules/Setup
        echo '_tcldis -L../../tcldis -l_tcldis' >> Modules/Setup
        # import site is really slow (doubles initialisation time) and we don't need it
        sed -i 's/^int Py_NoSiteFlag;/int Py_NoSiteFlag = 1;/' Python/pythonrun.c
        sed -i 's/^int Py_DontWriteBytecodeFlag;/int Py_DontWriteBytecodeFlag = 1;/' Python/pythonrun.c
        cat ../../emtcldis.c >> Python/pythonrun.c
        emmake make || true
        cp ../python.native python && chmod +x python
        emmake make
    cd ..
    ln -s ../../../tcldis/tcldis.py python/Lib
    sed -i 's|libz\.a$|\0 ../tcldis/opt/libtclpy/libtclpy.a ../tcldis/lib_tcldis.a ../emtcl/emtcl.bc|' Makefile
    sed -i 's/EXPORTED_FUNCTIONS=[^]]*/\0, '"'"'_emtcldis_init'"'"', '"'"'_emtcldis_decompile'"'"'/' Makefile
    sed -i 's/EXPORTED_FUNCTIONS=.*/\0 -s DEAD_FUNCTIONS="['"'"'_TclExecuteByteCode'"'"','"'"'_Tcl_NamespaceObjCmd'"'"']"/' Makefile
    make
    cp lp.js ../tcldis.js
    cd ..
