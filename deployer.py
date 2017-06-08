#!/usr/bin/env python3
# -*- coding: ascii -*-

# deployer.py -- A pipe-controlled script runner.

import argparse

def main():
    p = argparse.ArgumentParser()
    p.add_argument('-p', '--pipe', help='set control pipe location',
                   default='/var/run/deployer', dest='pipe')
    p.add_argument('-r', '--root', help='set script root location',
                   default='/usr/share/deployer', dest='root')
    res = p.parse_args()
    print (res)

if __name__ == '__main__': main()
