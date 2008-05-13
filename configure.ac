AC_INIT(src/__init__.py)

PACKAGE=mobile-manager
VERSION=0.1

AC_SUBST(PACKAGE)
AC_SUBST(VERSION)

AM_INIT_AUTOMAKE($PACKAGE, $VERSION)
AM_CONFIG_HEADER(config.h)

AM_MAINTAINER_MODE

AC_ISC_POSIX
AC_PROG_CC
AC_STDC_HEADERS
AM_DISABLE_STATIC
AC_PROG_LIBTOOL

AC_ARG_WITH(init-scripts,
  [  --with-init-scripts=[redhat/debian/suse/None]  Use TCP Wrappers [default=None]],,
  with_init_scripts=None)

AC_ARG_ENABLE(eggs-support,
  [  --enable-eggs-support=[yes/no]  Enable eggs support [default=no]],,
  enable_eggs_support=no)

dnl check for python
dnl ----------------------------
AM_PATH_PYTHON

PKG_CHECK_MODULES(PYGTK, pygtk-2.0 >= 2.6)
AC_SUBST(PYGTK_CFLAGS)
AC_SUBST(PYGTK_LIBS)

PKG_CHECK_MODULES(PYDBUS, dbus-python >= 0.80)
AC_SUBST(PYDBUS_CFLAGS)
AC_SUBST(PYDBUS_LIBS)

dnl check for python headers
dnl ------------------------------
AC_MSG_CHECKING(for shared library Python styff)

PY_PREFIX=`$PYTHON -c 'import sys ; print sys.prefix'`
PY_EXEC_PREFIX=`$PYTHON -c 'import sys ; print sys.exec_prefix'`
PYTHON_LIBS="-lpython$PYTHON_VERSION"
PYTHON_LIB_LOC="-L$PY_EXEC_PREFIX/lib/python$PYTHON_VERSION/config"
PYTHON_CFLAGS="-I$PY_PREFIX/include/python$PYTHON_VERSION"
PYTHON_MAKEFILE="$PY_EXEC_PREFIX/lib/python$PYTHON_VERSION/config/Makefile"
PYTHON_LOCALMODLIBS=`sed -n -e 's/^LOCALMODLIBS=\(.*\)/\1/p' $PYTHON_MAKEFILE`
PYTHON_BASEMODLIBS=`sed -n -e 's/^BASEMODLIBS=\(.*\)/\1/p' $PYTHON_MAKEFILE`
PYTHON_OTHER_LIBS=`sed -n -e 's/^LIBS=\(.*\)/\1/p' $PYTHON_MAKEFILE`
PYTHON_EXTRA_LIBS="$PYTHON_LOCALMODLIBS $PYTHON_BASEMODLIBS $PYTHON_OTHER_LIBS"
AC_SUBST([PYTHON_LIBS])
AC_SUBST([PYTHON_LIB_LOC])
AC_SUBST([PYTHON_CFLAGS])
AC_SUBST([PYTHON_EXTRA_LIBS])

rm -rf testpython
mkdir testpython
cd testpython
cat > testpython.c <<EOF
#include <Python.h>
int testpython (void)
{
Py_Exit (0);
}
EOF

if /bin/sh ../libtool --mode=compile ${CC} $PYTHON_CFLAGS -c testpython.c >/dev/null 2>&1 && \
/bin/sh ../libtool --mode=link ${CC} -o testpython.la -rpath `pwd` -module -avoid-version $PYTHON_LIB_LOC testpython.lo $PYTHON_LIBS $PYTHON_EXTRA_LIBS >/dev/null 2>&1 && \
grep 'dlname.*testpython' testpython.la >/dev/null 2>&1; then
	result=yes
else
	result=no
	have_python=no
fi
cd ..
rm -rf testpython

if test $result != "yes"
then
  AC_MSG_RESULT(not found)
  AC_MSG_ERROR([You need install the headers of Python (python-dev)])
else
  AC_MSG_RESULT(found)
fi		


dnl Other headers
dnl -----------------------------

PKG_CHECK_MODULES(HUAWEI220, libusb >=  0.1.12)
AC_SUBST(HUAWEI220_CFLAGS)
AC_SUBST(HUAWEI220_LIBS)

AC_PATH_PROG( PKGCONFIG, pkg-config, no, $PATH:/usr/bin:/usr/local/bin)
  if test "$PKGCONFIG" != "no" ; then
    AC_MSG_CHECKING([PYTHONPATH env variable for PyGTK])
    PYTHONPATH=$($PKGCONFIG --variable=pyexecdir pygtk-2.0)
    AC_SUBST([PYTHONPATH])
    AC_MSG_RESULT($PYTHONPATH)
  fi

export PYTHONPATH=$PYGTK_DIR:$PYTHONPATH

dnl check for libglade
dnl -----------------------------------------
AC_MSG_CHECKING(for gtk.glade)
prog="
import sys
try:
  import gtk.glade
except RuntimeError:
  sys.exit(0)
except ImportError:
  sys.exit(1)
sys.exit(0)
"

if $PYTHON -c "$prog" 1>&AC_FD_CC 2>&AC_FD_CC
then
  AC_MSG_RESULT(found)
else
  AC_MSG_RESULT(not found)
  AC_MSG_ERROR([You need to have python libglade bindings installed])
fi


dnl checking operative system
dnl --------------------------------------------

SYSCONFDIR_TMP="$sysconfdir"
EXPANDED_SYSCONFDIR=`eval echo $SYSCONFDIR_TMP`
AC_SUBST(EXPANDED_SYSCONFDIR)

operating_system=unknown

AC_MSG_CHECKING(Checking Redhat)
if test -f /etc/redhat-release || test -f $EXPANDED_SYSCONFDIR/redhat-release ; then
   AC_MSG_RESULT(found)
   operative_system=redhat
else
   AC_MSG_RESULT(not found)
fi

AC_MSG_CHECKING(Checking Suse)
if test -f /etc/SuSE-release || test -f $EXPANDED_SYSCONFDIR/SuSE-release ; then
   AC_MSG_RESULT(found)
   operative_system=suse
else
   AC_MSG_RESULT(not found)
fi

AC_MSG_CHECKING(Checking Debian/Ubuntu)
if test -f /etc/debian_version || test -f $EXPANDED_SYSCONFDIR/debian_version ; then
   AC_MSG_RESULT(found)
   operative_system=debian
else
   AC_MSG_RESULT(not found)
fi

AM_CONDITIONAL(MSD_INIT_SCRIPTS_RED_HAT, test x$with_init_scripts = xredhat)
AM_CONDITIONAL(MSD_INIT_SCRIPTS_SUSE, test x$with_init_scripts = xsuse)
AM_CONDITIONAL(MSD_INIT_SCRIPTS_DEBIAN, test x$with_init_scripts = xdebian)

if test "x$operative_system" = xsuse ; then
AM_CONDITIONAL(HAVE_UDEV_SUSE_RULES, true)
else
AM_CONDITIONAL(HAVE_UDEV_SUSE_RULES, false)
fi

if test "x$operative_system" = xredhat ; then
AM_CONDITIONAL(HAVE_UDEV_REDHAT_RULES, true)
else
AM_CONDITIONAL(HAVE_UDEV_REDHAT_RULES, false)
fi

if test "x$operative_system" = xdebian ; then
AM_CONDITIONAL(HAVE_UDEV_DEBIAN_RULES, true)
else
AM_CONDITIONAL(HAVE_UDEV_DEBIAN_RULES, false)
fi

AM_CONDITIONAL(MSD_EGGS_SUPPORT, test x$enable_eggs_support = xyes)



dnl *******************************
dnl Internationalization
dnl ******************************* 

GETTEXT_PACKAGE=mobile-manager
AC_DEFINE(GETTEXT_PACKAGE, "$GETTEXT_PACKAGE", "mobile-manager")
AC_SUBST(GETTEXT_PACKAGE)
dnl AC_CONFIG_MACRO_DIR([m4])
GNOME_DOC_INIT

dnl Add the languages which your application supports here.
ALL_LINGUAS="es"

AM_GLIB_GNU_GETTEXT
AC_PROG_INTLTOOL

AC_OUTPUT([
Makefile
po/Makefile.in
contrib/Makefile
contrib/huawei/Makefile
contrib/option/Makefile
contrib/novatel/Makefile
data/Makefile
data/dbus/Makefile
data/glade/Makefile
data/initscripts/Makefile
data/initscripts/debian/Makefile
data/initscripts/redhat/Makefile
data/initscripts/suse/Makefile
src/Makefile
src/ui/Makefile
src/ui/__init__.py
src/devices/Makefile
src/mmdt/Makefile
src/mmdt/mmdt
doc/Makefile
])

dnl ----------------------------------------------------------------

echo "
		MOVISTAR DESKTOP
		================

	prefix:				 ${prefix}
	sysconfdir:			 ${EXPANDED_SYSCONFDIR}
	with init scripts:		 ${with_init_scripts}

"
	
