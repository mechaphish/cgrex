
import os
import re
import utils
import tempfile
import shutil
import contextlib
from distutils.spawn import find_executable  

class VagrantManager:

    shared_folder_tag = "cgcrex_shared_tmp"

    def __init__(self,vgfile=None):
        assert (vgfile == None or os.path.exists(vgfile))
        self.vgfile = vgfile
        self.vagrant_cmd = find_executable("vagrant")

        if self.vgfile!=None:
            self.vgfolder = os.path.dirname(os.path.realpath(self.vgfile))
        else:
            self.vgfolder="/tmp"

        #TODO get these two by reading elf.vgfil
        self.shared_dir = self.vgfolder
        self.shared_remote_dir = "/vagrant"

        self.start_vm_if_necessary()


    @contextlib.contextmanager
    def get_shared_tmpdir(self,auto_delete=True):
        '''
        create a temporary folder, shared with the vm
        '''
        prefix = os.path.join(self.shared_dir,VagrantManager.shared_folder_tag)
        tmpdir = tempfile.mkdtemp(prefix=prefix)
        try:
            yield tmpdir
        finally:
            if auto_delete:
                shutil.rmtree(tmpdir)


    def start_vm_if_necessary(self):
        if self.vgfile==None or self.check_vm_status()=="running":
            return 

        print "+++","the vm is down, powering it up"
        res = utils.exec_cmd([self.vagrant_cmd] + ["up"],cwd=self.vgfolder)
        assert self.check_vm_status()=="running","the vm did not start: %s" % repr(res)


    def check_vm_status(self):
        assert self.vgfile!=None

        #TODO consider other cases: not existing, ...
        res = utils.exec_cmd([self.vagrant_cmd] + ["status"],cwd=self.vgfolder)
        for line in res[0].split("\n"):
            line = line.strip()
            if line.startswith("default"):
                if "running" in line:
                    return "running"
        return "non-running"


    def quote(self,s):
        #from shlex.quote
        if not s:
            return "''"
        # use single quotes, and put single quotes into double quotes
        # the string $'b is then quoted as '$'"'"'b'
        return "'" + s.replace("'", "'\"'\"'") + "'"


    def translate_and_quote(self,s):
        #this is somehow a heuristic, but it should be good
        if self.vgfile!=None:
            sep = os.path.sep
            bname = os.path.realpath(s)

            if bname.startswith(os.path.join(self.shared_dir,VagrantManager.shared_folder_tag)):
                #this is a path and it is inside a shared dir: convert it
                inside_path = bname[len(self.shared_dir)+1:]
                s = os.path.join(self.shared_remote_dir,inside_path)

        return self.quote(s)



    def exec_cmd(self,args,force_machine_up=False,debug=False):
        '''
        execute one or more commands within the Vagrant vm, if a self.vgfile!=None
        if args is a list of lists, multiple commands are executed in bash
        '''
        #TODO test inside vagrant (vgfile == None)

        if len(args)>0 and type(args[0])==list:
            #at the end every arg will be quoted twice
            targs = ";".join([" ".join([self.translate_and_quote(a) for a in c]) for c in args])
            processed_args = ["bash","-c"] + [targs]
        else:
            processed_args = args 


        if self.vgfile == None:
            #we are running inside the vm, just do normal execution
            res = utils.exec_cmd(processed_args,debug=debug)
            return res

        if force_machine_up:
            #checking the status every time slows down a lot
            #the machine should be (from when __init__ is called)
            if self.check_vm_status() != "running":
                self.start_vm_if_necessary()

        inner_args = [self.translate_and_quote(a) for a in processed_args]
        full_args = [self.vagrant_cmd,"ssh","--"] + inner_args
        #implicitly this seems to be called with shell=True
        res = utils.exec_cmd(full_args,cwd=self.vgfolder,debug=debug)
        return res




