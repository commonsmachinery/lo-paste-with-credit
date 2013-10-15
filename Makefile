#! /usr/bin/make -f

SOURCES = \
	description.xml \
	META-INF/manifest.xml \
	Addons.xcu \
	cm-paste.py

ADDITIONAL_PATHS = pythonpath

EXTENSION = paste_with_credit.oxt

all: $(EXTENSION)

$(EXTENSION):
	zip -r $(EXTENSION) \
		$(SOURCES) \
		$(ADDITIONAL_PATHS)

clean:
	rm $(EXTENSION)

install:
	unopkg add $(EXTENSION)

uninstall:
	unopkg remove $(EXTENSION)
