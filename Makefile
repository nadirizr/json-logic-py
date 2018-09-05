release:
	python setup.py bdist_wheel upload

clean:
	rm -rf build dist json_logic_qubit.egg-info
