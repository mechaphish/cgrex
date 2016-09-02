
import shutil
import os
import time
import timeout_decorator

from . import utils
from Fortifier import Fortifier
from QemuTracer import QemuTracer
from MiasmPatcher import MiasmPatcher

import angr


import logging
l = logging.getLogger('cgrex.CGRexAnalysis')


class CGRexAnalysisException(Exception):
    pass


class CGRexAnalysis:

    max_patching_tries = 5

    def __init__(self,binary_fname,out_fname,povs_fname):
        self.binary_fname = binary_fname
        self.out_fname = out_fname
        assert len(povs_fname)>0
        self.povs_fname = povs_fname

        self.tracer = QemuTracer()
        self.patcher = MiasmPatcher()

    @timeout_decorator.timeout(60*10)
    def create_cfg(self,p):
        ctime = time.time()
        l.debug("creating cfg...")
        cfg = p.analyses.CFG()
        cfg.normalize()
        l.debug("cfg done (%s)!"%(time.time()-ctime))
        return cfg


    def run(self):
        def gen_name(td,cb_num,ntry):
            return os.path.join(td,os.path.basename(self.binary_fname)+"_%06d_%06d"%(cb_num,ntry))


        l.info("working on binary: %s",self.binary_fname)
        base_code = utils.compile_asm_template("base1.asm",{'code_loaded_address':hex(Fortifier.fortify_segment1_base)})
        cb = Fortifier(self.binary_fname, base_code)

        crashes = 0
        with utils.tempdir() as td:

            total_tries = 0
            cb_num = -1
            for pov in self.povs_fname:
                cb_num+=1
                ntry = 0
                cb.save(gen_name(td,cb_num,ntry))
                shutil.copy(gen_name(td,cb_num,ntry),self.out_fname+"_tmp"+"_%06d_%06d"%(cb_num,ntry)) 

                while True:
                    l.info("working on pov: %s, try: %d",pov,ntry)
                    cb = Fortifier(gen_name(td,cb_num,ntry))

                    trace = self.tracer.trace_pov(pov,gen_name(td,cb_num,ntry))
                    if trace == None:
                        if ntry == 0:
                            l.info("pov did not generate any crash: %s",pov)
                            #FIXME how should we handle this?
                            #maybe we want to generate an exception only if total_tries == 0
                            #because in other cases a patch for a previous pov may have fixed the currently tested one
                            break
                        else:
                            l.info("cb is now immune to %s. after %d patches",pov,ntry)
                            break

                    angr_project = angr.Project(gen_name(td,cb_num,ntry))
                    try:
                        angr_cfg = self.create_cfg(angr_project)
                    except timeout_decorator.TimeoutError:
                        l.error("cfg timeout!")
                        angr_cfg = None
                        #FIXME (how can we handle this)

                    crashes += 1
                    if ntry > CGRexAnalysis.max_patching_tries:
                        raise CGRexAnalysisException("too many patching tries (%d)"%CGRexAnalysis.max_patching_tries)

                    patch_info = self.patcher.generate_patch_info(trace,cb,angr_cfg)
                    patch = self.patcher.add_code_to_patch_info(patch_info,cb)

                    print hex(Fortifier.fortify_segment1_base+len(cb.injected_code))
                    cb.insert_detour(Fortifier.fortify_segment1_base+len(cb.injected_code),patch)

                    ntry += 1
                    total_tries += 1
                    cb.save(gen_name(td,cb_num,ntry))
                    shutil.copy(gen_name(td,cb_num,ntry),self.out_fname+"_tmp"+"_%06d_%06d"%(cb_num,ntry))  

            if crashes==0:
                raise CGRexAnalysisException("no pov crashed, tested povs: %s"%repr(self.povs_fname))

            l.info("cb is now immune to %s after %d patches",repr(self.povs_fname),total_tries)
            shutil.copy(gen_name(td,cb_num,ntry),self.out_fname)            


