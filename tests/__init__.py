# See file COPYING distributed with dpf for copyright and license.

import os
import subprocess
import socket
import time

class ServerError(Exception):
    """server error"""

def start_data_server():

    if not os.path.exists('tmp'):
        os.mkdir('tmp')
    if not os.path.exists('tmp/data'):
        os.mkdir('tmp/data')

    fo_out = open('tmp/data_test.stdout', 'a')
    fo_err = open('tmp/data_test.stderr', 'a')

    po = subprocess.Popen(['dpf_data_server', 
                           '-C', 'tmp/data', 
                           '-H', 'dpf.data.handlers.CSVHandler', 
                           '-H', 'dpf.data.handlers.JSONHandler'],
                          stdout=fo_out, 
                          stderr=fo_err)

    # wait for the data server to be listening
    # if it doesn't come up after a certain amount of time, clean up and 
    # raise an error

    for i in xrange(5):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('localhost', 8080))
        except socket.error:
            time.sleep(1)
            pass
        else:
            break
        finally:
            s.close()
    else:
        po.terminate()
        fo_out.close()
        fo_err.close()
        raise ServerError()

    return (po, fo_out, fo_err)

def start_process_server():

    if not os.path.exists('tmp'):
        os.mkdir('tmp')
    if not os.path.exists('tmp/process'):
        os.mkdir('tmp/process')
    fo_out = open('tmp/process_test.stdout', 'a')
    fo_err = open('tmp/process_test.stderr', 'a')
    po = subprocess.Popen(['dpf_process_server', 
                           '-C', 'tmp/process', 
                           '-H', 'wc=dpf.process.handlers.WCHandler', 
                           '-H', 'echo=dpf.process.handlers.EchoHandler'], 
                          stdout=fo_out, 
                          stderr=fo_err)

    # wait for the data server to be listening
    # if it doesn't come up after a certain amount of time, clean up and 
    # raise an error

    for i in xrange(5):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('localhost', 8081))
        except socket.error:
            time.sleep(1)
            pass
        else:
            break
        finally:
            s.close()
    else:
        po.terminate()
        fo_out.close()
        fo_err.close()
        raise ServerError()

    return (po, fo_out, fo_err)

def stop_server(po, fo_out, fo_err):
    po.terminate()
    fo_out.close()
    fo_err.close()
    return

# eof
