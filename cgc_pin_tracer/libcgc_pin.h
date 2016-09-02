#ifndef _LIBCGC_PIN_H
#define _LIBCGC_PIN_H

//NOTE: I just prefixed everything with CGC or cgc 
// so that these declarations are different from the standard (e.g. linux)
// ones.

#define CGC_STDIN 0
#define CGC_STDOUT 1
#define CGC_STDERR 2

#ifndef NULL
#define NULL ((void *)0)
#endif

typedef long unsigned int cgc_size_t;
typedef long signed int cgc_ssize_t;

#define CGC_SSIZE_MAX       2147483647
#define CGC_SIZE_MAX        4294967295
#define CGC_FD_SETSIZE      1024

typedef long int cgc_fd_mask;

#define CGC_NFDBITS (8 * sizeof(cgc_fd_mask))

typedef struct {
        cgc_fd_mask _fd_bits[CGC_FD_SETSIZE / CGC_NFDBITS];
} cgc_fd_set;

#define CGC_FD_ZERO(set)                                                    \
        do {                                                            \
                cgc_size_t __i;                                                \
                for (__i = 0; __i < (CGC_FD_SETSIZE / CGC_NFDBITS); __i++)     \
                        (set)->_fd_bits[__i] = 0;                               \
        } while (0)
#define CGC_FD_SET(b, set) \
        ((set)->_fd_bits[b / CGC_NFDBITS] |= (1 << (b & (CGC_NFDBITS - 1))))
#define CGC_FD_CLR(b, set) \
        ((set)->_fd_bits[b / CGC_NFDBITS] &= ~(1 << (b & (CGC_NFDBITS - 1))))
#define CGC_FD_ISSET(b, set) \
        ((set)->_fd_bits[b / CGC_NFDBITS] & (1 << (b & (CGC_NFDBITS - 1))))

struct cgc_timeval {
        int tv_sec;
        int tv_usec;
};

#define CGC_EBADF           1
#define CGC_EFAULT          2
#define CGC_EINVAL          3
#define CGC_ENOMEM          4
#define CGC_ENOSYS          5
#define CGC_EPIPE           6

//Some additional definitions
#define _TERMINATE 1
#define _TRANSMIT 2
#define _RECEIVE 3
#define _FDWAIT 4
#define _ALLOCATE 5
#define _DEALLOCATE 6
#define _RANDOM 7

#define CGC_PAGE_SIZE   4096
#define CGC_PAGE_MASK   (~(CGC_PAGE_SIZE - 1))

#endif /* _LIBCGC_PIN_H */



