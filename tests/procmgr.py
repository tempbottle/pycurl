import threading
import subprocess
import os
import sys
import signal

from . import runwsgi

class ProcessManager(object):
    def __init__(self, cmd):
        self.cmd = cmd
    
    def start(self):
        self.process = subprocess.Popen(self.cmd)
        
        self.thread = threading.Thread(target=self.run)
        self.thread.daemon = True
        self.thread.start()
    
    def run(self):
        self.process.communicate()

managers = {}

def start(cmd):
    if str(cmd) in managers:
        # already started
        return
    
    manager = ProcessManager(cmd)
    managers[str(cmd)] = manager
    manager.start()

def start_setup(cmd):
    def do_start():
        start(cmd)
    return do_start

# Example on FreeBSD:
# PYCURL_VSFTPD_PATH=/usr/local/libexec/vsftpd nosetests

if 'PYCURL_VSFTPD_PATH' in os.environ:
    vsftpd_path = os.environ['PYCURL_VSFTPD_PATH']
else:
    vsftpd_path = 'vsftpd'

def vsftpd_setup():
    config_file_path = os.path.join(os.path.dirname(__file__), 'vsftpd.conf')
    root_path = os.path.join(os.path.dirname(__file__), '..')
    cmd = [
        vsftpd_path,
        config_file_path,
        '-oanon_root=%s' % root_path,
    ]
    setup_module = start_setup(cmd)
    def do_setup_module():
        try:
            setup_module()
        except OSError:
            import errno
            e = sys.exc_info()[1]
            if e.errno == errno.ENOENT:
                msg = "Tried to execute `%s`\nTry specifying path to vsftpd via PYCURL_VSFTPD_PATH environment variable\n" % vsftpd_path
                raise OSError(e.errno, e.strerror + "\n" + msg)
            else:
                raise
        ok = runwsgi.wait_for_network_service(('127.0.0.1', 8321), 0.1, 10)
        if not ok:
            import warnings
            warnings.warn('vsftpd did not start after 1 second')
    
    def teardown_module():
        try:
            manager = managers[str(cmd)]
        except KeyError:
            pass
        else:
            try:
                os.kill(manager.process.pid, signal.SIGTERM)
            except OSError:
                pass
    
    return do_setup_module, teardown_module
