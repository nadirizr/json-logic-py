release:
	python setup.py bdist_wheel upload -r local

clean:
	rm -rf build dist json_logic_qubit.egg-info
