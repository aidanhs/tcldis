from __future__ import print_function

import os
import json
from textwrap import dedent

import tclpy
import tcldis

import bottle
from bottle import route, request, response, static_file

ROOT = os.path.dirname(__file__)

@route('/')
def index():
    return static_file('index.html', root=ROOT)

@route('/static/<path:path>')
def static_srv(path):
    return static_file(path, root=ROOT)

@route('/api/decompile_steps', method='POST')
def decompile_steps():
    tcl = request.json
    proctcl = 'proc p {} {\n' + tcl + '\n}'
    tclpy.eval(proctcl)
    steps, changes = tcldis.decompile_steps(tcldis.getbc(proc_name='p'))
    return json.dumps({'steps': steps, 'changes': changes})

def start():
    # Start the server
    host = '127.0.0.1'
    port = int(os.environ.get('TCLDIS_PORT', 8000))
    bottle.debug(True)
    try:
        import cherrypy
        bottle.run(host=host, port=port, server='cherrypy')
    except:
        print("WARNING: falling back to single threaded mode")
        bottle.run(host=host, port=port)

if __name__ == '__main__':
    start()
