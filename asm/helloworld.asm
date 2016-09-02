USE32
org {code_loaded_address}

_start
    pusha
    mov eax, _str_hello
    call _prints

    popa
    jmp {code_return}

;_iloop:
;    jmp _iloop

_prints ;eax=buf(null terminates)
    pusha
    xor ebx,ebx
    xor edx,edx
    xor ecx,ecx
    _prints_loop
        mov ebx,eax
        add ebx,ecx
        mov dl,[ebx]
        inc ecx
        test edx,edx
        jne _prints_loop
    dec ecx
    mov ebx,ecx
    call _print
    popa
    ret

_print ;eax=buf,ebx=len
    pusha
    mov ecx,eax
    mov edx,ebx
    mov eax,0x2
    mov ebx,0x1
    mov esi,0x0
    int 0x80
    popa
    ret
   
_str_hello:
    db '=== Hello world!',0xa,0x00



