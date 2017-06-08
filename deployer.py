#!/usr/bin/env python3
# -*- coding: ascii -*-

# deployer.py -- A simple script runner.

import os
import threading
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
        elif ch == '\n':
            break
        else:
            sb.append(ch)
    return ''.join(r)

def setup_socket(path):
    try:
        os.unlink(path)
    except IOError as e:
        if e.errno != errno.ENOENT:
            raise
    sock = socket.socket()
    sock.bind(path)
    os.fchmod(sock, stat.S_IRUSR | stat.S_IWUSR)
    sock.listen(5)
    return sock

def handler(conn, addr, root):
    try:
        # Read request line
        request = readline(conn).split()
        if len(request) != 2 or request[0] != 'RUN':
            conn.sendall(b'ERROR Bad request\n')
            return
        elif '/' in request[1]:
            conn.sendall(b'ERROR Bad filename\n')
            return
        # Locate script
        # You don't use UTF-8? Shame upon yourself!
        path = os.path.join(root.encode('utf-8'), request[1])
        if not os.path.isfile(path):
            conn.sendall(b'ERROR No such file or directory\n')
            return
        elif not os.access(path, os.X_OK):
            conn.sendall(b'ERROR Permission denied\n')
            return
        # Start it
        conn.sendall(b'OK\n')
        proc = subprocess.Popen([path], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=0)
        # Run select loop
        ctpbuf, ptcbuf = '', ''
        while not eofc or not eofp:
            rlist, wlist = [], []
            if eofc:
                pass
            elif ctpbuf:
                wlist.append(proc.stdin)
            else:
                rlist.append(conn)
            if eofp:
                pass
            elif ptcbuf:
                wlist.append(conn)
            else:
                rlist.append(proc.stdout)
            nrl, nwl, nxl = select.select(rlist, wlist, ())
            if conn in rlist:
                r = conn.recv(4096)
                if not r: eofc = True
                ctpbuf += r
            if proc.stdout in rlist:
                r = proc.stdin.read(4096)
                if not r: eofp = True
                ptcbuf += r
            if proc.stdin in wlist:
                n = proc.stdin.write(ctpbuf)
                ctpbuf = ctpbuf[n:]
            if conn in wlist:
                n = conn.send(ptcbuf)
                ptcbuf = ptcbuf[n:]
    except EOFError:
        pass
    finally:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except IOError:
            pass
        try:
            conn.close()
        except IOError:
            pass

def main():
    p = argparse.ArgumentParser()
    p.add_argument('-s', '--socket', help='set control socket location',
                   default='/var/run/deployer', dest='socket')
    p.add_argument('-r', '--root', help='set script root location',
                   default='/usr/share/deployer', dest='root')
    res = p.parse_args()
    sock = setup_socket(res.socket)
    while 1:
        conn, addr = sock.accept()
        spawn_thread(handler, conn, addr, res.root)
        conn, addr = None, None

if __name__ == '__main__': main()
