udevdir = $(sysconfdir)/udev/rules.d
udev_DATA = 04-huawei.rules


INCLUDES = $(LIBUSB_CFLAGS)

sbin_PROGRAMS = huaweiAktBbo1003 huaweiAktBbo1004 huaweiAktBbo1406

huaweiAktBbo1406_LDADD = $(LIBUSB_LIBS)
huaweiAktBbo1406_SOURCES = huaweiAktBbo-pid-1406.c

huaweiAktBbo1004_LDADD = $(LIBUSB_LIBS)
huaweiAktBbo1004_SOURCES = huaweiAktBbo-pid-1004.c

huaweiAktBbo1003_LDADD = $(LIBUSB_LIBS)
huaweiAktBbo1003_SOURCES = huaweiAktBbo-pid-1003.c


EXTRA_DIST= 04-huawei.rules 
