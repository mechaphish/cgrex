USE32
org {code_loaded_address}

_saved_esp:
    db 0x0,0x0,0x0,0x0
_saved_eax:
    db 0x0,0x0,0x0,0x0

CGREX_memcheck_and_exit_ptr:
    db 0xc,0x0,0x0,0x9

CGREX_memcheck_and_exit: ;eax=address,ebx=size,ecx=flags([write][read])
    pusha
    mov edx,eax
    and edx,0xfffff000
    mov esi,eax
    add esi,ebx
    dec esi
    and esi,0xfffff000

    mov eax,edx
    call _memcheck_and_exit_int
    mov eax,esi
    call _memcheck_and_exit_int

    popa
    ret

CGREX_print_eax:
    pusha
    mov ecx,32
    mov ebx,eax
    _print_reg_loop:
        rol ebx,4
        mov edi,ebx
        and edi,0x0000000f
        lea eax,[_print_hex_array+edi]
        mov ebp,ebx
        mov ebx,0x1
        call _print
        mov ebx,ebp
        sub ecx,4
        jnz _print_reg_loop
    mov eax,_new_line
    mov ebx,1
    call _print
    popa
    ret


CGREX_exit:
    pusha
    mov eax,1 ;_terminate
    ;TODO return something related to detour point (but return value is ANDed with 0xff)
    mov ebx,0x85 ;133
    int 0x80 ;this may actually not terminate due to the pin counter-hack
    popa
    ret

_memcheck_and_exit_int: ;eax=address,ecx=flags([write][read])
    pusha
    ;int3
    mov ebp,eax
    xor edx,edx
    mov edi,ecx
    and edi,0x00000001
    test edi,edi
    je _out1
        call _test_read
        test eax,eax
        jne _out1
            call CGREX_exit
    _out1:
    ;int3
    mov eax,ebp
    mov edi,ecx
    and edi,0x00000002
    test edi,edi
    je _out2
        call _test_write
        test eax,eax
        jne _out2
            call CGREX_exit
    _out2
    popa
    ret

_test_read:
    ;call CGREX_print_eax
    pusha
    cmp eax, 0x1000
    jb _fail_read
    mov esi,eax
    mov eax,4 ;fdwait
    xor ebx,ebx
    dec ebx ;nfds<0
    xor ecx,ecx
    xor edx,edx
    mov edi,0x0 ;passing syscall arguments in edi does not seem to work!
    int 0x80
    ;jmp _iloop
    ;int3

    cmp eax,3 ;EFAULT
    jne _fail_read
    xor eax,eax
    inc eax
    jmp _end_test_read
    _fail_read:
        xor eax,eax
    _end_test_read:

    mov [_garbage_area],eax
    popa
    mov eax,[_garbage_area]
    ret

_test_write:
    ;call CGREX_print_eax
    pusha
    cmp eax, 0x1000
    jb _fail_write
    mov edx,eax
    mov eax,7 ;random
    xor ebx,ebx
    xor ecx,ecx

    mov edi,[edx] ; FIXME hack that assumes that this area is 4-byte readable
    mov [_garbage_area],edi
    int 0x80
    mov edi,[_garbage_area]
    mov [edx],edi

    test eax,eax
    jne _fail_write
    xor eax,eax
    inc eax
    jmp _end_test_write
    _fail_write:
        xor eax,eax
    _end_test_write:

    mov [_garbage_area],eax
    popa
    mov eax,[_garbage_area]
    ret


_print: ;eax=buf,ebx=len
    pusha
    mov ecx,eax
    mov edx,ebx
    mov eax,0x2
    mov ebx,0x1
    mov esi,0x0
    int 0x80
    popa
    ret


_new_line:
    db 0xa
_print_hex_array:
    db '0','1','2','3','4','5','6','7','8','9','a','b','c','d','e','f'
_garbage_area:
    db 0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0
    db 0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0,0x0


; === END_BASE
