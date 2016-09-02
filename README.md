# CGrex
**WARNING: this project is obsolete.**

**CGrex was used only during the CGC qualifier event, for the final event we used [Patcherex](https://github.com/shellphish/patcherex).**

CGrex is a targeted patcher for CGC binaries.

We used it (together with fidget) just for the CGC qualifier event.

CGrex takes as an input a CGC binary and a list of POVs and it generates a binary that (supposedly) it is not vulnerable anymore to those POVs. 

In a nutshell, CGrex works by injecting code that "abuses" return values of the `random` and `fdwait` syscalls to detect if the soon-to-be-accessed memory regions are allocated.


## Installation
```bash
# install requirements
sudo apt-get install socat

# create a virtualenv
mkvirtualenv cgrex

# download cgrex
git clone https://github.com/mechaphish/cgrex.git

# install Python requirements
cd cgrex
pip install -r reqs.txt

#install miasm
git clone https://github.com/cea-sec/miasm.git
cd miasm
pip install -e .
cd ..
```

## Usage
```bash
main.py --binary=<binary> --out=<out> <povs>...
```
Example:
```bash
./main.py --binary tests/0b32aa01/0b32aa01_01 --out /tmp/0b32aa01_01_cgrex1 tests/0b32aa01/0b32aa01_01.xml tests/0b32aa01/0b32aa01_02.xml
```
`/tmp/0b32aa01_01_cgrex1` is now "immune" to the two POVs.
For instance, it should not segfault with the following input:
```bash
python -c 'print "A"*100' | bin/qemu-cgc /tmp/0b32aa01_01_cgrex1
```

## How does CGrex work?
During the CGC qualification event an input generating a crash (encoded in a POV) was a considered as a vulnerability. The goal of CGrex is just to generate a binary that does not crash, when provided with a previously crashing input.

CGrex works in five steps.

1) Run the CGC binary against a given POV (using `bin/qemu-cgc`).

2) Detect the instruction pointer where the POV generates a crash (the "culprit instruction").

3) Extract the symbolic expression of the memory accesses performed by the "culprit instruction" (by using miasm).

4) Generate "checking" code that dynamically:

* Compute the memory accesses that the "culprit instruction" is going to perform.

* Verify that these memory accesses are within allocated memory regions (and so the "culprit instruction" is not going to crash). To understand if some memory is allocated or not CGrex "abuses" the return values of the `random` and `fdwait` syscalls.

* If a memory access outside allocated memory is detected, the injected code just calls `exit`.

5) Inject the "cheking" code.

Steps 1 to 5 are repeated until the binary does not crash anymore with all the provided POVs.


