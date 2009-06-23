AC_PREREQ(2.52)
AC_INIT(ubiquity, 1.13, https://launchpad.net/ubuntu/+source/ubiquity/+filebug)
AC_CONFIG_SRCDIR(src/cut-and-paste/gdm-signal/gdm-logout-action.c)
AC_CONFIG_AUX_DIR([build])
AC_CONFIG_MACRO_DIR([m4])
AM_INIT_AUTOMAKE([foreign])

AM_CONFIG_HEADER(config.h)

AM_MAINTAINER_MODE

AM_PROG_LIBTOOL

AM_GNU_GETTEXT([external])
AM_GNU_GETTEXT_VERSION([0.17])

IT_PROG_INTLTOOL([0.40.0], [no-xml])

AC_ISC_POSIX
AC_PROG_CC
AC_HEADER_STDC
AC_PROG_INSTALL
AC_PROG_MAKE_SET

GTK_REQUIRED=2.10.0

if test "x$UBIQUITY_NO_GTK" = x; then
  PKG_CHECK_MODULES(GTK, [glib-2.0 gtk+-2.0 >= $GTK_REQUIRED])
  AC_SUBST(GTK_CFLAGS)
  AC_SUBST(GTK_LIBS)
  AM_PATH_GTK_2_0([$GTK_REQUIRED])
  AC_CONFIG_FILES(
	src/Makefile
	src/cut-and-paste/Makefile
	src/cut-and-paste/gdm-signal/Makefile
	)
else
  AC_SUBST(GTK_CFLAGS, [])
  AC_SUBST(GTK_LIBS, [])
fi

AC_DEFINE_UNQUOTED(PIXMAPS_DIR, "${datadir}/${PACKAGE}/pixmaps", [pixmaps directory])
pixmapsdir="${datadir}/${PACKAGE}/pixmaps"
AC_SUBST(pixmapsdir)

AC_CONFIG_FILES(
	Makefile
	desktop/Makefile
	pixmaps/Makefile
	po/Makefile.in
	)
AC_OUTPUT
