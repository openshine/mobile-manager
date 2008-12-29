%define is_mandrake %(test -e /etc/mandrake-release && echo 1 || echo 0)
%define is_suse %(test -e /etc/SuSE-release && echo 1 || echo 0)
%define is_fedora %(test -e /etc/fedora-release && echo 1 || echo 0)

Name: mobile-manager
Summary: Mobile Manager daemon (GPRS/3g support)
Version: 0.8
Release: 1 
License: GPLv2+
Group: Applications/Internet
Source: mobile-manager-%{version}.tar.gz

BuildRoot:  %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)

Requires: gtk2 >= 2.4.0
Requires: python
Requires: libusb

%if %is_suse
Requires: python-gtk
Requires: dbus-1
Requires: dbus-1-python
%endif 

%if %is_fedora
Requires: pygtk2
Requires: dbus
Requires: dbus-python
%endif 

%if %is_suse
BuildRequires: python-gtk-devel
BuildRequires: dbus-1-python-devel
BuildRequires: dbus-1-glib-devel
BuildRequires: dbus-1-devel
%endif

%if %is_fedora
BuildRequires: pygtk2-devel
BuildRequires: dbus-devel >= 0.90
BuildRequires: dbus-python-devel
%endif 

BuildRequires: automake
BuildRequires: autoconf
BuildRequires: python-devel
BuildRequires: gettext
BuildRequires: gcc

%if %is_suse
BuildRequires: gnome-doc-utils-devel
%endif

%if %is_fedora
BuildRequires: gnome-doc-utils
%endif 

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

%if 0%{?suse_version} > 1020 

%configure --prefix=/usr --sysconfdir=/etc  --with-init-scripts=suse
make %{?_smp_mflags}

%else 

%configure --prefix=/usr --sysconfdir=/etc  --with-init-scripts=redhat
make %{?_smp_mflags}

%endif 

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

if [ -f /etc/init.d/udev ] && [ -x /etc/init.d/udev ] ; then
        /etc/init.d/udev reload
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
* Mon Dec 29 2008 Roberto Majadas <roberto.majadas@openshine.com> - 0.8-1
- New upstream version
* Wed Jun 25 2008 Roberto Majadas <roberto.majadas@openshine.com> - 0.7-1
- New upstream version
* Fri Jun 20 2008 Roberto Majadas <roberto.majadas@openshine.com> - 0.6-2
- Fedora and opensuse support
* Thu Jun 19 2008 Roberto Majadas <roberto.majadas@openshine.com> - 0.6-1
- Initial
