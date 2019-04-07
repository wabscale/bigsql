# Python
MAIN_NAME=dev.py
ENV_NAME=venv
PYTHON_VERSION=`which python3.7`

.PHONY: all run setup clean

all: setup

test:
	coverage run --omit="venv/*" dev.py
	coverage report

setup:
	if [ -d ${ENV_NAME} ]; then \
		rm -rf ${ENV_NAME}; \
	fi
	if [ -a requirements.txt ]; then \
		touch requirements.txt; \
	fi
	which virtualenv && pip install virtualenv || true
	virtualenv -p ${PYTHON_VERSION} ${ENV_NAME}
	./${ENV_NAME}/bin/pip install -r requirements.txt

run:
	if [ ! -d ${ENV_NAME} ]; then \
		make setup; \
	fi
	./${ENV_NAME}/bin/python ${MAIN_NAME}

clean:
	if [ -d ${ENV_NAME} ]; then \
		rm -rf ${ENV_NAME}; \
	fi
	if [ -n "`find . -name __pycache__`" ]; then \
		rm -rf `find . -name __pycache__`; \
	fi
