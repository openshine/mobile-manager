SUBDIRS = ui mmdt devices messaging pdu 

sbin_SCRIPTS = MobileManagerDaemon

mobilemanagerdir = $(pythondir)/MobileManager
mobilemanager_PYTHON = 	__init__.py			\
			MobileController.py		\
			MobileManagerDbus.py		\
			MobileDialWvdial.py		\	
			MobileDial.py			\
			MobileDevice.py			\
			MobileStatus.py			\
			MobileCapabilities.py		\
			daemon.py


INCLUDES = 	-I$(top_srcdir)			\
		-I$(top_srcdir)/src		\
		$(PYTHON_CFLAGS)

pkgpyexecdir = $(pythondir)/MobileManager

pkgpyexec_LTLIBRARIES = mdpc.la

mdpc_la_SOURCES = mdpcmodule.c
mdpc_la_LDFLAGS =  -module -avoid-version -export-symbols-regex initmdpc
mdpc_la_LIBADD = $(PYTHON_LIBS)

EXTRA_DIST=MobileManagerDaemon
