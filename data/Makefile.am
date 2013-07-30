SUBDIRS = icons

@INTLTOOL_DESKTOP_RULE@

desktopdir = $(datadir)/applications
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)
desktop_in_files = \
	oem-config-prepare-gtk.desktop.in \
	oem-config-prepare-kde.desktop.in \
	ubiquity-gtkui.desktop.in \
	ubiquity-kdeui.desktop.in

@INTLTOOL_POLICY_RULE@

polkit_policydir = $(datadir)/polkit-1/actions
polkit_policy_in_files = com.ubuntu.ubiquity.policy.in
polkit_policy_DATA = $(polkit_policy_in_files:.policy.in=.policy)

EXTRA_DIST = $(desktop_in_files) $(polkit_policy_in_files)

CLEANFILES = $(desktop_DATA)
