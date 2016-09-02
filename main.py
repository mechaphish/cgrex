#!/usr/bin/env python

import os
import docopt
import sys
from cgrex.CGRexAnalysis import CGRexAnalysis


import logging
logging.root.addHandler(logging.StreamHandler(sys.stdout))
l = logging.getLogger('cgrex.main')

ARGS = '''
Usage:
    main.py --binary=<binary> --out=<out> <povs>...
'''



def main():
    args = docopt.docopt(ARGS)
    l.debug(repr(args))


    if os.path.isdir(args["<povs>"][0]):
        povlist = os.listdit(args["<povs>"][0])
    else:
        povlist = args["<povs>"]

    cga = CGRexAnalysis(args["--binary"],args["--out"],args["<povs>"])
    cga.run()


if __name__ == "__main__":
    logging.getLogger('cgrex.main').setLevel(logging.DEBUG)
    logging.getLogger('cgrex.CGRexAnalysis').setLevel(logging.DEBUG)
    logging.getLogger('cgrex.QemuTracer').setLevel(logging.DEBUG)
    logging.getLogger('cgrex.MiasmPatcher').setLevel(logging.DEBUG)
    logging.getLogger('cgrex.Fortifier').setLevel(logging.DEBUG)
    logging.getLogger('angr.analyses.cfg').setLevel(logging.DEBUG)

    sys.exit(main())



'''
./main.py --binary tests/0b32aa01/0b32aa01_01 --out /tmp/0b32aa01_01_cgrex1 tests/0b32aa01/0b32aa01_01.xml tests/0b32aa01/0b32aa01_02.xml
'''


