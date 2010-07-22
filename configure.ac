AC_PREREQ(2.52)
AC_INIT([ubiquity], [2.3], [https://launchpad.net/ubuntu/+source/ubiquity/+filebug])
AC_CONFIG_SRCDIR([src/panel/panel.c])
AC_CONFIG_AUX_DIR([build])
AC_CONFIG_MACRO_DIR([m4])
AM_INIT_AUTOMAKE([foreign])

AM_CONFIG_HEADER([config.h])

AM_MAINTAINER_MODE

AM_PROG_LIBTOOL

AM_GNU_GETTEXT([external])
AM_GNU_GETTEXT_VERSION([0.17])

GETTEXT_PACKAGE=ubiquity
AC_SUBST([GETTEXT_PACKAGE])
IT_PROG_INTLTOOL([0.40.0], [no-xml])

AC_PROG_CC
AC_HEADER_STDC
AC_PROG_INSTALL
AC_PROG_MAKE_SET

GTK_REQUIRED=2.10.0

dnl TODO replace GTK GTK_CFLAGS ... with BASE or PANEL
if test "x$UBIQUITY_NO_GTK" = x; then
  PKG_CHECK_MODULES(BASE, [glib-2.0
			  gtk+-2.0 >= $GTK_REQUIRED
			  indicator
			  x11])
  AC_SUBST(BASE_CFLAGS)
  AC_SUBST(BASE_LIBS)
  AM_PATH_GTK_2_0([$GTK_REQUIRED])
  AC_CONFIG_FILES(
	src/Makefile
	src/panel/Makefile
	)
else
  AC_SUBST(BASE_CFLAGS, [""])
  AC_SUBST(BASE_LIBS, [""])
fi


AM_PATH_PYTHON([2.6])
UBIQUITY_CHECK_PYTHON_HEADERS(,[AC_MSG_ERROR([could not find Python headers])])

AC_CHECK_FUNCS([setresuid setresgid getresuid getresgid])

AC_DEFINE_UNQUOTED(PIXMAPS_DIR, "${datadir}/${PACKAGE}/pixmaps", [pixmaps directory])
pixmapsdir="${datadir}/${PACKAGE}/pixmaps"
AC_SUBST([pixmapsdir])

AC_CONFIG_FILES([
	Makefile
	desktop/Makefile
	pixmaps/Makefile
	po/Makefile.in
	ubiquity/Makefile
	])
AC_OUTPUT
