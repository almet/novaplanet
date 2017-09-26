VIRTUALENV = virtualenv --python=python3
SPHINX_BUILDDIR = docs/_build
VENV := $(shell realpath $${VIRTUAL_ENV-.venv})
PYTHON = $(VENV)/bin/python3
DEV_STAMP = $(VENV)/.dev_env_installed.stamp
DOC_STAMP = $(VENV)/.doc_env_installed.stamp
INSTALL_STAMP = $(VENV)/.install.stamp
TEMPDIR := $(shell mktemp -d)

all: install
install: virtualenv $(INSTALL_STAMP)
$(INSTALL_STAMP):
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -r requirements.txt
	touch $(INSTALL_STAMP)

virtualenv: $(PYTHON)
$(PYTHON):
	$(VIRTUALENV) $(VENV)

serve: install
	$(PYTHON) -m SimpleHTTPServer

clean:
	rm -rf .venv

generate: $(INSTALL_STAMP)
	$(PYTHON) scrap.py output
