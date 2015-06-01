#Makefile for creating plumetrack distributions


docs:
	@echo "Auto-generating API documentation"
	sphinx-apidoc -f -o doc/source src/plumetrack
	@echo "Building HTML documetation"
	cd doc; make html
	@echo "setting MIME types"
	cd doc; ./set_mime_types.sh
	@echo "Done building documentation"

clean:
	@echo "Removing build dir"
	rm -rf build
	@echo "Removing dist dir"
	rm -rf dist
	@echo "Removing MANIFEST file"
	rm -f MANIFEST

.PHONY: icons
icons:
	@echo "Generating sized icons from SVG files"
	cd src/plumetrack/icons; python create_sized_icons.py
	
.PHONY: build
build: icons
	@echo "Creating wrappers using SWIG"
	cd src/swig; swig -c++ -python gpu_motion.i
	@echo "Copying auto-generated .py files to src folder"
	cp src/swig/*.py src/
	@echo "Building..."
	python setup.py build

install: build
	python setup.py install

dist: docs icons
	@echo "Creating source dist"
	python setup.py sdist
	@echo "Creating examples archive"
	rm -f dist/Plumetrack_examples.zip
	zip -r dist/Plumetrack_examples examples -i examples/*\[^~\]
	@echo "Creating 32-bit Windows installer"
	wine "C:\\Python27_32\\python.exe" setup.py skip_checks bdist_wininst --install-script=plumetrack_win32_postinstall.py
	@echo "Creating 64-bit Windows installer"
	wine64 "C:\\Python27_64\\python.exe" setup.py skip_checks bdist_wininst --install-script=plumetrack_win32_postinstall.py
    
