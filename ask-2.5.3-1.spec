Summary: Active Spam Killer
Name: ask
Version: 2.5.3
Release: 1
License: GPL
Group: Applications/Mail
Source: http://prdownloads.sourceforge.net/ask-2.5.3.tar.gz
URL: http://www.paganini.net/ask
BuildArch: noarch
BuildRoot: /tmp/%{name}-root
Requires: python

##
##	Macros
##

%define	packager		Marco Paganini
%define	distribution	Marco Paganini
%define	vendor			www.paganini.net
%define	_signature		gpg
%define	_gpg_name		Marco Paganini

%define	_tmppath	/tmp/ask-packages
%define	_topdir		%{_tmppath}
%define	_rpmtopdir	%{_topdir}/dist
%define	_builddir	%{_topdir}/BUILD
%define	_rpmdir		%{_rpmtopdir}
%define	_sourcedir	%{_rpmtopdir}
%define	_specdir	%{_rpmtopdir}
%define	_srcrpmdir	%{_rpmtopdir}

%description
Active Spam Killer (ASK) protects your email account against spam by
confirming the sender's email address before actual delivery takes
place. The confirmation happens by means of a "confirmation message" that
is automatically sent to all "unknown" users. Once the sender replies to
that message (a simple reply will do), future emails from that person will
be delivered immediately. You can also specify (regexp) addresses to be
immediately accepted, rejected (with a nastygram) or ignored. The package
also includes a utility to scan your old mailboxes and generate a list of
emails to be accepted automatically.

%prep
%setup -q

%build
%install

##
##	At this point, the current directory will contain the
##	unpacked contents of the .tar.gz file.
##

install -d -m 755 %{buildroot}/usr/bin
install -d -m 755 %{buildroot}/usr/lib/ask
install -d -m 755 %{buildroot}/usr/share/ask
install -d -m 755 %{buildroot}/usr/share/man/man1
install -d -m 755 %{buildroot}/usr/share/ask/templates

install -m 755 askfilter asksetup utils/asksenders %{buildroot}/usr/bin
install -m 644 askversion.py  %{buildroot}/usr/lib/ask
install -m 644 askconfig.py   %{buildroot}/usr/lib/ask
install -m 644 asklock.py     %{buildroot}/usr/lib/ask
install -m 644 asklog.py      %{buildroot}/usr/lib/ask
install -m 644 askmail.py     %{buildroot}/usr/lib/ask
install -m 644 askmain.py     %{buildroot}/usr/lib/ask
install -m 644 askmessage.py  %{buildroot}/usr/lib/ask
install -m 644 askremote.py   %{buildroot}/usr/lib/ask

install -m 644 templates/* %{buildroot}/usr/share/ask/templates

gzip -9 docs/*.1 || true
install -m 644 docs/*.1.gz %{buildroot}/usr/share/man/man1

#install -m 644 utils/*     %{buildroot}/usr/share/ask/utils

%clean
rm -rf %{buildroot}

%files
%defattr(-, root, root)
%doc COPYING ChangeLog TODO docs/ask_doc.html docs/ask_doc.css docs/ask_doc.pdf docs/ask_doc.txt

##
##	Here we list all the files installed by the RPM
##

/usr/bin/askfilter
/usr/bin/asksetup
/usr/bin/asksenders
/usr/lib/ask/askversion.py
/usr/lib/ask/askconfig.py
/usr/lib/ask/asklock.py
/usr/lib/ask/asklog.py
/usr/lib/ask/askmail.py
/usr/lib/ask/askmain.py
/usr/lib/ask/askmessage.py
/usr/lib/ask/askremote.py
/usr/share/man/man1/askfilter.1.gz
/usr/share/man/man1/asksenders.1.gz
/usr/share/man/man1/asksetup.1.gz
/usr/share/ask/templates/ignorelist.txt
/usr/share/ask/templates/whitelist.txt
/usr/share/ask/templates/ask.rc
/usr/share/ask/templates/confirm_da.txt
/usr/share/ask/templates/confirm_de.txt
/usr/share/ask/templates/confirm_en.txt
/usr/share/ask/templates/confirm_es.txt
/usr/share/ask/templates/confirm_fi.txt
/usr/share/ask/templates/confirm_fr.txt
/usr/share/ask/templates/confirm_it.txt
/usr/share/ask/templates/confirm_nl.txt
/usr/share/ask/templates/confirm_ptbr.txt
