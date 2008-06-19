Name: mobile-manager
Summary: Mobile Manager daemon (GPRS/3g support)
Version: 0.6
Release: 1%{?dist}
License: GPLv2+
Group: Applications/Internet
Source: mobile-manager-%{version}.tar.gz

BuildRoot:  %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires: gtk2 >= 2.4.0
Requires: python
Requires: dbus-1-python
Requires: python-gtk
Requires: libusb
Requires: dbus-1

BuildRequires: python-gtk-devel
BuildRequires: dbus-1-python-devel
BuildRequires: dbus-1-glib-devel
BuildRequires: dbus-1-devel
BuildRequires: automake
BuildRequires: autoconf
BuildRequires: python-devel
BuildRequires: gettext
BuildRequires: gcc
BuildRequires: gnome-doc-utils-devel
BuildRequires: intltool
BuildRequires: libtool
BuildRequires: libusb-devel


%description
Mobile Manager is a GPRS/3G daemon developed by Telefonica. 
This daemon cover the GPRS/3G funtions for develop and work
over GPRS/3G

%prep
%setup -q 

%build
%configure --prefix=/usr --sysconfdir=/etc  --with-init-scripts=suse
make %{?_smp_mflags}


%install
rm -rf $RPM_BUILD_ROOT
make install DESTDIR=$RPM_BUILD_ROOT

%files
%{_bindir}/*
%{_sbindir}/*
%{_sysconfdir}/*
%{_libdir}/*
%{_datadir}/*


%clean
rm -rf $RPM_BUILD_ROOT

%post
/sbin/ldconfig
/sbin/chkconfig --add mobile-manager

dbus-send --print-reply --system --type=method_call \
            --dest=org.freedesktop.DBus \
            / org.freedesktop.DBus.ReloadConfig > /dev/null

if [ -f /etc/init.d/boot.udev ] && [ -x /etc/init.d/boot.udev ] ; then
	/etc/init.d/boot.udev reload
fi

if [ -f /etc/init.d/mobile-manager ] && [ -x /etc/init.d/mobile-manager ] ; then
	/etc/init.d/mobile-manager start
fi



%preun
if [ $1 = 0 ]; then
    service mobile-manager stop > /dev/null 2>&1
    /sbin/chkconfig --del mobile-manager
fi

%changelog
* Tue Nov 6 2007 Roberto Majadas <roberto.majadas@openshine.com> - 0.6
- Initial
