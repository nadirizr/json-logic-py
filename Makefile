release: build
	python setup.py bdist_wheel upload -r local

build: clean
	python setup.py bdist_wheel

clean:
	rm -rf build dist json_logic_qubit.egg-info
