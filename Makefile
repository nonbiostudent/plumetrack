#Makefile for creating plumetrack distributions


#get the version number from the python code
VERSION != more src/plumetrack/__init__.py | grep VERSION | cut -d '"' -f2

docs:
	@echo "Auto-generating API documentation"
	sphinx-apidoc -f -o doc/source src/plumetrack
	@echo "Building HTML documetation"
	cd doc; make html
	#@echo "setting MIME types"
	#cd doc; ./set_mime_types.sh
	@echo "Done building documentation"

clean:
	@echo "Removing build dir"
	rm -rf build
	@echo "Removing dist dir"
	rm -rf dist
	@echo "Removing MANIFEST file"
	rm -f MANIFEST
	@echo "Removing pyinstaller files"
	rm -f src/plumetrack_gui_??.??.py
	rm -f plumetrack_gui_??.??.spec
	
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

dist: docs icons frozen_bin
	@echo "Creating source dist"
	python setup.py sdist
	@echo "Creating examples archive"
	rm -f dist/Plumetrack_examples.zip
	zip -r dist/Plumetrack_examples examples -i examples/*\[^~\]
	@echo "Creating 32-bit Windows installer"
	wine "C:\\Python27_32\\python.exe" setup.py skip_checks bdist_wininst --install-script=plumetrack_win32_postinstall.py
	@echo "Creating 64-bit Windows installer"
	wine64 "C:\\Python27_64\\python.exe" setup.py skip_checks bdist_wininst --install-script=plumetrack_win32_postinstall.py

frozen_bin: icons
	@echo "from plumetrack.gui import main\n" > "src/plumetrack_gui_$(VERSION).py"
	@echo "main.main()\n" >> "src/plumetrack_gui_$(VERSION).py"
	
	wine "C:\\users\\nial\\Anaconda2\\Scripts\\pyinstaller" -F --noconsole --add-data="src\\plumetrack\\icons;plumetrack\\icons" --hidden-import=scipy._lib.messagestream --icon="src/plumetrack/icons/plumetrack.ico" "src/plumetrack_gui_$(VERSION).py"
	

#	~/.local/bin/pyinstaller -F --console --add-data="plumetrack/icons:plumetrack/icons" --icon="plumetrack/icons/plumetrack.ico" plumetrack_gui.py

# wine "C:\\users\\nial\\Anaconda2\\Scripts\\pyinstaller" -F --console --add-data="plumetrack\\icons;plumetrack\\icons" --hidden-import=scipy._lib.messagestream --icon="plumetrack/icons/plumetrack.ico" plumetrack_gui.py
