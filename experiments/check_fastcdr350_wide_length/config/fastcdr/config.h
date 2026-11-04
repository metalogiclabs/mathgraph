#ifndef _FASTCDR_CONFIG_H_
#define _FASTCDR_CONFIG_H_
#define FASTCDR_VERSION_MAJOR 2
#define FASTCDR_VERSION_MINOR 4
#define FASTCDR_VERSION_MICRO 0
#define FASTCDR_VERSION_STR "2.4.0"
#define HAVE_CXX11 1
#define FASTCDR_IS_BIG_ENDIAN_TARGET 0
#define FASTCDR_HAVE_FLOAT128 0
#define FASTCDR_SIZEOF_LONG_DOUBLE 16
#if defined(__GNUC__) && !defined(__clang__)
#define TEMPLATE_SPEC
#else
#define TEMPLATE_SPEC template<>
#endif
#endif
