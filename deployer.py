#!/usr/bin/env python3
# -*- coding: ascii -*-

# deployer.py -- A simple script runner.

import os
import threading
import signal
import socket
import select
import stat
import errno
import subprocess
import argparse

def spawn_thread(func, *args, **kwds):
    thr = threading.Thread(target=func, args=args, kwargs=kwds)
    thr.setDaemon(True)
    thr.start()
    return thr

def readline(sock):
    r = []
    while 1:
        ch = sock.recv(1)
        if not ch:
            raise EOFError
        elif ch == b'\n':
            break
        else:
            r.append(ch)
    return b''.join(r)

class Deployer:
    def __init__(self, sockpath, sockmode, scriptroot):
        self.sockpath = sockpath
        self.sockmode = sockmode
        self.scriptroot = scriptroot
        self.cond = threading.Condition()
        self._running = {}
        self._following = {}
        self._nextid = 0
        self.socket = None
    def setup_socket(self):
        try:
            os.unlink(self.sockpath)
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket.bind(self.sockpath)
        # Cannot fchmod() socket as the bind() applies the umask.
        os.chmod(self.sockpath, self.sockmode)
        self.socket.listen(5)
        return self.socket
    def handler(self, conn, addr):
        running = None
        try:
            # Read request line
            request = readline(conn).split()
            if len(request) != 2 or request[0] != b'RUN':
                conn.sendall(b'ERROR Bad request\n')
                return
            elif b'/' in request[1]:
                conn.sendall(b'ERROR Bad filename\n')
                return
            # Locate script
            # You don't use UTF-8? Shame upon yourself!
            path = os.path.abspath(os.path.join(
                self.scriptroot.encode('utf-8'), request[1]))
            if not os.path.isfile(path):
                conn.sendall(b'ERROR No such file or directory\n')
                return
            elif not os.access(path, os.X_OK):
                conn.sendall(b'ERROR Permission denied\n')
                return
            # Determine if (and when) we are going to run it
            sent_ok = False
            with self.cond:
                # Grab a waiting number
                this_id = self._nextid
                self._nextid += 1
                # Relieve any pending thread
                self._following[path] = this_id
                self.cond.notifyAll()
                # Wait until the previous instance (if any) is done
                while 1:
                    if self._following[path] != this_id:
                        # Someone came after us; bye
                        return
                    elif not self._running.get(path):
                        # Our turn!
                        if not sent_ok: conn.sendall(b'OK\n')
                        break
                    else:
                        # We have to wait
                        if not sent_ok: conn.sendall(b'OK WAIT\n')
                        sent_ok = True
                    self.cond.wait()
                self._running[path] = True
                running = path
            # Start it
            proc = subprocess.Popen([path], stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
            # Run select loop
            ctpbuf, ptcbuf, eofc, eofp = b'', b'', False, False
            while ctpbuf or ptcbuf or not eofc or not eofp:
                rlist, wlist = [], []
                if ctpbuf:
                    wlist.append(proc.stdin)
                elif not eofc:
                    rlist.append(conn)
                if ptcbuf:
                    wlist.append(conn)
                elif not eofp:
                    rlist.append(proc.stdout)
                nrl, nwl, nxl = select.select(rlist, wlist, ())
                if conn in nrl:
                    r = conn.recv(4096)
                    if not r: eofc = True
                    ctpbuf += r
                if proc.stdout in nrl:
                    r = proc.stdout.read(4096)
                    if not r:
                        eofp = True
                        conn.shutdown(socket.SHUT_WR)
                    ptcbuf += r
                if proc.stdin in nwl:
                    n = proc.stdin.write(ctpbuf)
                    ctpbuf = ctpbuf[n:]
                if conn in nwl:
                    n = conn.send(ptcbuf)
                    ptcbuf = ptcbuf[n:]
        except EOFError:
            pass
        finally:
            if running is not None:
                with self.cond:
                    self._running[running] = False
                    self.cond.notifyAll()
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except IOError:
                pass
            try:
                conn.close()
            except IOError:
                pass
    def main(self):
        self.setup_socket()
        try:
            while 1:
                conn, addr = self.socket.accept()
                spawn_thread(self.handler, conn, addr)
                conn, addr = None, None
        finally:
            self.cleanup_socket()
    def cleanup_socket(self):
        try:
            self.socket.close()
        except (AttributeError, socket.error):
            pass
        try:
            os.unlink(self.sockpath)
        except IOError:
            pass

def main():
    def octal(s):
        return int(s, 8)
    def interrupt(signo, frame):
        if signo == signal.SIGINT:
            raise KeyboardInterrupt
        else:
            raise SystemExit
    p = argparse.ArgumentParser()
    p.add_argument('-s', '--socket', help='set control socket location',
                   default='/var/run/deployer', dest='socket')
    p.add_argument('-m', '--mode', help='set (octal) control socket access '
                   'mode', default=384, type=octal, dest='mode') # 0600
    p.add_argument('-r', '--root', help='set script root location',
                   default='/usr/share/deployer', dest='root')
    signal.signal(signal.SIGINT, interrupt)
    signal.signal(signal.SIGTERM, interrupt)
    res = p.parse_args()
    inst = Deployer(res.socket, res.mode, res.root)
    try:
        inst.main()
    except (KeyboardInterrupt, SystemExit):
        pass

if __name__ == '__main__': main()
