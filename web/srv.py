from __future__ import print_function

import os

import tclpy
import tcldis

import bottle
from bottle import route, request, response, static_file

@route('/')
def index():
    return static_file('index.html', root='.')

@route('/static/<path:path>.js')
def static_srv(path):
    return static_file(path + '.js', root='.')

def start():
    # Start the server
    host = '0.0.0.0'
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
