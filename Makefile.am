SUBDIRS = po contrib data src doc

intltool_extra = intltool-extract.in intltool-merge.in intltool-update.in

CLEANFILES = \
	configure.in

DISTCLEANFILES =		\
	intltool-extract	\
	intltool-merge		\
	intltool-update		\
	po/.intltool-merge-cache \
	gnome-doc-utils.make

EXTRA_DIST = \
	gnome-doc-utils.make 	\
	$(intltool_extra)	\	
        AUTHORS                 \
        NEWS                    \
        README 


#Ignore scrollkeeper files
DISTCHECK_CONFIGURE_FLAGS = --disable-scrollkeeper
