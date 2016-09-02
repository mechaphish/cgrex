
import os
from . import utils

import logging
l = logging.getLogger('cgrex.QemuTracer')



class QemuTracer:
    self_path = os.path.dirname(os.path.abspath(__file__))
    shm_folder = "/dev/shm"
    qemu_circular_buffer_split = "==========SPLIT==========\n"
    qemu_signal_log_line = "qemu: uncaught target signal"
    qemu_launcher_timeout = 75


    def __init__(self):
        pass


    def uncircle_string(self,tstr):
        l,_,r = tstr.partition(QemuTracer.qemu_circular_buffer_split)
        return r+l


    def trace_pov(self,pov,cb_fname):
        def line_to_bbinfo(line):
            if line.startswith("IN:"):
                p = line.split("[")[1].split("]")[0]
                bbstart = int(p.split(",")[0],16)
                bbsize = int(p.split(",")[1],16)
            elif line.startswith("Trace "):
                plist = line.split()[2:4]
                bbstart = int(plist[0],16)
                bbsize = int(plist[1],10)
            return (bbstart,bbsize)


        def remove_dups(seq):
           noDupes = []
           [noDupes.append(i) for i in reversed(seq) if not noDupes.count(i)]
           return noDupes


        with utils.tempdir(os.path.join(QemuTracer.shm_folder,"QemuTracer")) as td:
            args =  ["timeout",
                    "-k",
                    str(QemuTracer.qemu_launcher_timeout+5),
                    str(QemuTracer.qemu_launcher_timeout),
                    "./qemu_launcher.sh",
                    "./qemu_bb_wrap.sh",
                    os.path.abspath(cb_fname),os.path.abspath(pov),td]
            res = utils.exec_cmd(args,cwd=os.path.join(QemuTracer.self_path,"../bin/"))
            l.debug("running: %s"%" ".join(args))
            l.debug("results:")
            l.debug(res[0])
            l.debug(res[1])
            l.debug(res[2])
            qemu_log = self.uncircle_string(open(os.path.join(td,"qemu_log.txt")).read())
            l.debug(qemu_log)

            signal_lines = [line for line in qemu_log.split("\n") if line.startswith(QemuTracer.qemu_signal_log_line)]
            l.debug("signal lines:%s"%repr(signal_lines))
            if len(signal_lines) == 0:
                return None

            trace_info = {}
            signal_line = signal_lines[0]
            trace_info["Signal"] = int(signal_line.split(QemuTracer.qemu_signal_log_line)[1].split()[0])
            trace_info["LastIP1"] = int(signal_line.split("[")[1].split("]")[0],16)

            to_be_parsed_lines = [line for line in qemu_log.split("\n") if \
                    (line.startswith("Trace ") or line.startswith("IN:"))]

            itrace = remove_dups([line_to_bbinfo(line) for line in to_be_parsed_lines])

            trace_info["LastBB1addr"],trace_info["LastBB1size"] = itrace[0]
            trace_info["LastBB2addr"],trace_info["LastBB2size"] = itrace[1]

            l.debug("pov_trace: %s"%" - ".join([k+":"+hex(trace_info[k]) for k in trace_info.keys()]))
            return trace_info


        