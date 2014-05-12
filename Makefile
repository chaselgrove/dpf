# See file COPYING distributed with dpf for copyright and license.

default : build

build : dist/dpf-0.1.0.tar.gz

dist/dpf-0.1.0.tar.gz : 
	python setup.py sdist

register : 
	python setup.py register

upload : 
	python setup.py sdist upload

check : 
	python setup.py check
	rst2html.py --halt=2 README.rst > /dev/null

clean : 
	rm -f MANIFEST

clobber : clean
	rm -rf dist

# eof
