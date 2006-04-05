unexport DH_OPTIONS

APTDIR := apt
LISTDIR := lists
SOURCEDIR := source

ifndef DEB_HOST_ARCH
DEB_HOST_ARCH := $(shell dpkg-architecture -qDEB_HOST_ARCH)
endif

PACKAGES := $(shell cat $(LISTDIR)/any)
ifneq (,$(wildcard $(LISTDIR)/$(DEB_HOST_ARCH)))
PACKAGES += $(shell cat $(LISTDIR)/$(DEB_HOST_ARCH))
endif

update:
	./get-sources update
	./get-sources $(shell cat $(LISTDIR)/*)
	./update-control
	./update-changelog

maintainer-clean:
	rm -rf $(SOURCEDIR)

build:
	set -e; for package in $(PACKAGES); do \
		if [ -d "$(SOURCEDIR)/$$package" ]; then \
			(cd "$(SOURCEDIR)/$$package" && debian/rules build); \
		fi; \
	done

clean:
	rm -rf $(APTDIR)
	for dir in $(SOURCEDIR)/*; do \
		if [ -d "$$dir" ]; then \
			(cd "$$dir" && debian/rules clean); \
		fi; \
	done
	rm -f $(SOURCEDIR)/*.deb $(SOURCEDIR)/*.udeb
	rm -f manifest.old
	rm -rf udeb-control templates

install:
	set -e; for package in $(PACKAGES); do \
		if [ -d "$(SOURCEDIR)/$$package" ]; then \
			(cd "$(SOURCEDIR)/$$package" && \
			 debian/rules binary-arch && \
			 debian/rules binary-indep && \
			 rm -rf debian/*/DEBIAN); \
		fi; \
	done
	rm -rf udeb-control templates
	mkdir -p udeb-control
	set -e; for udeb in $(SOURCEDIR)/*.udeb; do \
		if [ -f "$$udeb" ]; then \
			name="$$(basename "$$udeb" .udeb)"; \
			dpkg-deb -e "$$udeb" "udeb-control/$$name"; \
			if [ -f "udeb-control/$$name/templates" ]; then \
				cat "udeb-control/$$name/templates" >> templates; \
				echo >> templates; \
			fi; \
		fi; \
	done

.PHONY: update build clean install
