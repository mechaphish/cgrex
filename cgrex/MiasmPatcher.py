
import os
import utils
import sys
import StringIO
from miasm2.ir.symbexec import symbexec
from miasm2.analysis.machine import Machine
from Fortifier import Fortifier


import logging
l = logging.getLogger('cgrex.MiasmPatcher')


class MiasmPatcherException(Exception):
    pass

class MiasmPatcher:

    def __init__(self):
        pass


    #TODO find a way to decompile at address,  this will make fails less severs
    #(but right now we cannot handle instructions influenced by position in any case)
    def execc(self,code):
        machine = Machine('x86_32')
        mdis = machine.dis_engine(code)
        blocs = mdis.dis_multibloc(0)
        ira = machine.ira()
        for b in blocs:
            ira.add_bloc(b)
        sb = symbexec(ira, machine.mn.regs.regs_init)
        sb.emul_ir_blocs(ira, 0)
        return sb
    '''
    mov saved_esp,esp
    mov esp, shadow_stack_start
    ...
    mov esp, saved_esp
    #ESP --> shadow_stack_start
    '''

    '''
        pusha
        lea eax, [...]
        mov ebx,4
        mov ecx,3
        call CGREX_memcheck_and_exit
        popa
    '''

    # this is the worst code I have ever written in my life :-)
    def protect_access(self,tstr,access,size,final_deref=False):
        def format_str(tstr):
            tstr = tstr.replace("_init","").replace("(","").replace(")","")
            tstr = ' '.join(tstr.split())
            tstr = tstr.replace("*"," * ").replace("+"," + ")
            return tstr


        def compile_token(token):
            token = token.strip().lower()
            if token == "esp":
                token = "[{_saved_esp}]"
            if token == "eax":
                token = "[{_saved_eax}]"
            return token

        def find_nested(tstr,n):
            level = 0
            offsets = []
            start = -1
            for i,c in enumerate(tstr):
                if c == "(":
                    level += 1
                if c == ")":
                    if level == n:
                        stop = i
                        offsets.append((start,stop))
                        start = -1
                    level -= 1
                if level == n and start == -1:
                    start = i
            return offsets


        l.debug("original expression: %s"%tstr)


        #moving nested expressions at the end (compiled first)
        #cannot work woth multiple nested expressions, but it should never be the case
        nested = find_nested(tstr,2)
        if len(nested)>1:
            raise MiasmPatcherException("expression with multiple nesting: "%tstr)
        for s,e in nested:
            if tstr[s-1] == "+" or tstr[s-1] == "*":
                tstr = tstr[:s-1]+tstr[e+1:]+tstr[s-1:e+1]
            else:
                tstr = tstr[:s]+tstr[e+2:]+tstr[e+1]+tstr[s-1:e+1]

        tstr = format_str(tstr)
        inner_assembly = []
        tokens = list(reversed(tstr.split()))
        l.debug("tokenized expression: %s"%repr(tstr))

        inner_assembly.append("mov eax, %s"%compile_token(tokens[0]))
        for token1,token2 in zip(tokens[1:],tokens[2:])[::2]:
            if token1 == "+":
                inner_assembly.append("add eax, %s"%compile_token(token2))
            elif token1 == "*":
                inner_assembly.append("imul eax, %s"%compile_token(token2))
            else:
                raise MiasmPatcherException("found weird token: %s"%token1)
        if final_deref:
            inner_assembly += ["mov eax, [eax]"]
        final_assembly = ["pusha"]+inner_assembly+["mov ebx,%d"%size,"mov ecx,%d"%access]+\
                ["call [{CGREX_memcheck_and_exit_ptr}]","popa"]

        patch_str = "\n".join(final_assembly)
        return patch_str

    
        #TODO many wild assumptons about what can appear in a single instruction and what not
    def parse_reg_diff(self,miasm_str):
        patches = []
        for line in miasm_str.split("\n"):
            if line.strip() == "":
                continue
            if ("X " in line or line.startswith("XMM") or line.startswith("zf ")) and "[" in line:
                patches.append(self.protect_access(line.split("[")[1].split("]")[0],1,4))
            if line.startswith("EIP"):
                if("[" in line):
                    patches.append(self.protect_access(line.split("[")[1].split("]")[0],1,4))
                    patches.append(self.protect_access(line.split("[")[1].split("]")[0],1,4,True))
                else:
                    patches.append(self.protect_access(line.split(" ")[1],1,4))
        return patches


    def parse_mem_diff(self,miasm_str):
        patches = []
        for line in miasm_str.split("\n"):
            if line.strip() == "":
                continue
            if "] " in line:
                patches.append(self.protect_access(line.split("[")[1].split("]")[0],3,4)) #FIXME permission should be 2, but becuase of the test_write problem I cneed it to be also readable
        return patches


    def generate_patch_info(self,trace_info,cb,cfg):
        patch_info = {}

        if "LastIP2" not in trace_info:
            last_bb_data = cb.get_maddress(trace_info["LastBB1addr"],trace_info["LastBB1size"])
            last_instruction = utils.decompile(last_bb_data,trace_info["LastBB1addr"])[-1]
            trace_info["LastIP2"] = int(last_instruction.address)
            l.debug("LastIP2 (from last bb): %s"%hex(trace_info["LastIP2"]))

        if ('X' in cb.get_memory_permissions(trace_info["LastIP1"])):
            culprit_address = trace_info["LastIP1"]
            l.debug("using LastIP1: %s"%hex(culprit_address))
        elif (trace_info["LastIP2"] != None and 'X' in cb.get_memory_permissions(trace_info["LastIP2"])):
            culprit_address = trace_info["LastIP2"]
            l.debug("using LastIP2: %s"%hex(culprit_address))
 
        if culprit_address >= trace_info["LastBB1addr"] and \
                culprit_address < (trace_info["LastBB1addr"] + trace_info["LastBB1size"]):
            bbstart = trace_info["LastBB1addr"]
            bbsize = trace_info["LastBB1size"]
        elif trace_info["LastBB2addr"] != None and \
                culprit_address >= trace_info["LastBB2addr"] and \
                culprit_address < (trace_info["LastBB2addr"] + trace_info["LastBB2size"]):
            bbstart = trace_info["LastBB2addr"]
            bbsize = trace_info["LastBB2size"]

        patch_info['bbstart'] = bbstart
        patch_info['bbsize'] = bbsize
        if cfg != None:
            l.info("culprit address to angr %s"%hex(culprit_address))
            angr_bb = cfg.get_any_node(culprit_address, is_syscall=False, anyaddr=True)
            if angr_bb != None:
                if angr_bb.size != None and angr_bb.size != 0:
                    angr_bbstart = int(angr_bb.addr)
                    angr_bbsize = int(angr_bb.size)
                    if angr_bbstart >= bbstart and (angr_bbstart+angr_bbsize <= bbstart+bbsize):
                        patch_info['bbstart'] = angr_bbstart
                        patch_info['bbsize'] = angr_bbsize
                        if angr_bbstart!=bbstart or angr_bbstart!=bbstart:
                            l.info("basicblocks do not match angr: %s-%s qemu: %s-%s"%(hex(angr_bbstart),angr_bbsize,hex(bbstart),bbsize))
                        else:
                            l.info("angr basicblock match angr: %s-%s qemu: %s-%s"%(hex(angr_bbstart),angr_bbsize,hex(bbstart),bbsize))
                    else:
                        l.info("angr basicblock is outsize angr: %s-%s qemu: %s-%s"%(hex(angr_bbstart),angr_bbsize,hex(bbstart),bbsize))
                        #TODO we may want to check if this is because partial overwrite
                else:
                    l.info("angr basicblock problem (size is None or 0)")
            else:
                l.info("angr basicblock problem (bb is None)")
        else:
            l.info("angr cfg is None")


        patch_info['culprit_address'] = culprit_address

        return patch_info



    def add_code_to_patch_info(self,patch_info,cb):
        culprit_address = patch_info['culprit_address']
        bbsize = patch_info['bbsize']
        bbstart = patch_info['bbstart']
        culprit_upto_bb_limit = cb.get_maddress(culprit_address,bbsize - (culprit_address-bbstart))
        #get only culprit
        culprit_instrucion = utils.decompile(culprit_upto_bb_limit)[0]
        culprit = culprit_upto_bb_limit[:culprit_instrucion.size]
        #culprit = utils.compile_asm("mov ecx, byte [ebp]")

        dec = utils.decompile(culprit,culprit_address)[0]
        l.debug("the culprit is: %s %s %s"%(hex(culprit_address),culprit.encode('hex'),utils.instruction_to_str(dec)))
        #culprit = utils.compile_asm("call [100+ecx*2+esp]")


        stdout = StringIO.StringIO()
        stderr = StringIO.StringIO()
        #this is terrible: since I did not want to parse miasm expressions, I just parse the string
        with utils.redirect_stdout(stdout,stderr):
            sb = self.execc(culprit)

        patches = []
        with utils.redirect_stdout(stdout,stderr):
            sb.dump_id()
        l.debug("raw miasm results regs:\n%s\n"%stdout.getvalue())
        patches += self.parse_reg_diff(stdout.getvalue())
        stdout = StringIO.StringIO()
        stderr = StringIO.StringIO()
        with utils.redirect_stdout(stdout,stderr):
            sb.dump_mem()
        l.debug("raw miasm results mem:\n%s\n"%stdout.getvalue())
        patches += self.parse_mem_diff(stdout.getvalue())

        patches = ["mov [{_saved_esp}],esp","mov [{_saved_eax}],eax","mov esp, {_shadow_stack}"]+patches+["mov esp, [{_saved_esp}]"]

        l.debug("fixing the culprit: %s %s"%(dec.mnemonic, dec.op_str))
        l.debug("with:\n"+"\n".join(patches))

        substitution_dict = {
            "_saved_esp":hex(Fortifier.fortify_segment1_base),
            "_saved_eax":hex(Fortifier.fortify_segment1_base+4),
            "CGREX_memcheck_and_exit_ptr":hex(Fortifier.fortify_segment1_base+8),
            "_shadow_stack":hex(Fortifier.fortify_segment2_base+0xf00)
        }
        fixed_patches = [line.format(**substitution_dict) for line in patches]
        l.debug("fixed patches:\n"+"\n".join(fixed_patches))
        patch_info["code"] = "\n".join(fixed_patches)
        return patch_info


