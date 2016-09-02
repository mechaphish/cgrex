

import os
import re
import utils
import tempfile
import shutil
import contextlib
import json
import time
import sys
from distutils.spawn import find_executable  


class PinManager:

    pin_download_link = "http://software.intel.com/sites/landingpage/pintool/downloads/pin-2.14-67254-gcc.4.4.7-linux.tar.gz"
    pin_installation_folder = "/vagrant/pin"
    pin_executable = os.path.join(pin_installation_folder,"pin")
    pin_module = "cgc_pin_tracer"
    pin_module_folder = os.path.join(os.path.split(os.path.split(os.path.abspath(__file__))[0])[0],pin_module)

    def __init__(self,vagrant_manager,pin_installation_folder=None):
        if pin_installation_folder != None:
            self.pin_installation_folder = pin_installation_folder
        self.vgm = vagrant_manager

        res = self.vgm.exec_cmd(["stat",self.pin_executable])
        if res[2] != 0:
            print "cannot find pin executable (inside the vm) in:",self.pin_executable
            print "download it from:",self.pin_download_link
            print "unpack it here (inside the vm):",self.pin_installation_folder
            sys.exit(1)


    def trace_exploit(self,executable_fname,exploit_fname):
        #TODO make the pintool directly output json
        def naive_parser(keys,content):
            res = {}
            for line in content.split("\n"):
                for k in keys:
                    if line.startswith(k):
                        res[k]=int(line.split(":")[1].strip(),16)
            return res

        with self.vgm.get_shared_tmpdir() as tf:
            executable_cgc_tmp_fname = os.path.join(tf,os.path.basename(executable_fname)+"_cgc")
            executable_elf_tmp_fname = os.path.join(tf,os.path.basename(executable_fname)+"_elf")
            exploit_tmp_fname = os.path.join(tf,os.path.basename(exploit_fname))
            result_tmp_fname = os.path.join(tf,"pin_module","cgc_pin_tracer_results.out")
            pinlog_tmp_fname = os.path.join(tf,"pin_module","pin.log")
            pin_module_tmp_fname = os.path.join(tf,"pin_module")

            shutil.copyfile(executable_fname,executable_cgc_tmp_fname)
            shutil.copyfile(executable_fname,executable_elf_tmp_fname)
            shutil.copyfile(exploit_fname,exploit_tmp_fname)
            shutil.copytree(self.pin_module_folder,pin_module_tmp_fname)

            res = self.vgm.exec_cmd([
                    ["cd",pin_module_tmp_fname],
                    ["make","PIN_ROOT="+self.pin_installation_folder,"clean"],
                    ["make","PIN_ROOT="+self.pin_installation_folder]
            ])
            if res[2] != 0:
                print "error %d while compiling the pin module"%res[2]
                print res[0]
                print res[1]
                return None

            '''
            The wrapping made by cgc-server (or cgc-test since it uses cgc-server) is incompatible with pin.
            In fact, it, for instance, forbid to open new files and a lot of other bad stuff.
            Netcat can do the same.
            from pin_module: nc -e ./pin_wrap.sh   -l 127.0.0.1  -p 10000 &
            from tf: cb-replay --host 127.0.0.1 --port 10000 pov-1.xml
            I do not know hot to pss an argument to pin_wrap.sh, just create and use a harcoded link
            '''
            #set permissions and links
            #I use links since I do not know how to pass parameters to netcat -e
            #It seems that cb-reply does not like links
            #the big assumption is that the test is going to make the execution of the program end AND crash
            res = self.vgm.exec_cmd([
                ["killall","test.sh"],
                ["cgc2elf",executable_elf_tmp_fname],
                ["chmod","755",executable_cgc_tmp_fname],
                ["chmod","755",executable_elf_tmp_fname],
                ["ln","-s",executable_elf_tmp_fname,os.path.join(pin_module_tmp_fname,"binary")],
                ["ln","-s",self.pin_executable,os.path.join(pin_module_tmp_fname,"pin_binary")],
                ["cd",pin_module_tmp_fname],
                ["./test.sh",exploit_tmp_fname]
            ])
            #TODO adapt for multi-binary programs
            #TODO check if it actually crashed (and timeout if no response)
            #TODO the current pintool is tracing at instruction level: a better solution would be to
            #first trace at bb level and rerun tracing at instruction level only within the crashing bb
            print "===","TEST RESULTS:"
            print "=","STDOUT:\n",res[0].strip()
            print "=","STDERR:\n",res[1].strip()
            print "=","RETURN CODE:",res[2]

            if(os.path.exists(pinlog_tmp_fname)):
                pinlog_res = open(pinlog_tmp_fname).read()
            else:
                pinlog_res = None
            if(os.path.exists(result_tmp_fname)):
                raw_res = open(result_tmp_fname).read()
            else:
                result_tmp_fname = None
            raw_input()

        if pinlog_res != None:
            print "=","PIN LOG:"
            print pinlog_res        

        if raw_res != None:
            print "=","PIN RESULT:"
            print raw_res
            res_keys = ["LastIP1","LastIP2","LastBB1addr","LastBB1size","LastBB2addr","LastBB2size","Signal","ExitCode"]
            res = naive_parser(res_keys,raw_res)
            return res
        else:
            return None




