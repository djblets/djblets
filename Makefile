PYTHON=python3
PIP=${PYTHON} -m pip


develop:
	${PIP} install -e . --config-settings editable_mode=compat
	${PIP} install -r dev-requirements.txt


.PHONY: develop
