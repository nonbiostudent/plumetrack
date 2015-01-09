%module gpu_motion

%{
#define SWIG_FILE_WITH_INIT
#include <numpy/arrayobject.h>
#include "gpu_motion.h"

%}

%include "numpy.i"
%init %{
import_array();
%}

%exception GPUInterface::computeFlow{
	int err = $action
	
	if (err != 0){
		setPythonTraceback();
		SWIG_fail;
	}
}

%exception GPUInterface::testArray{
	int err = $action
	
	if (err != 0){
		setPythonTraceback();
		SWIG_fail;
	}
}

%apply (double *IN_ARRAY2, int DIM1, int DIM2) {(double *im1, int im1_height, int im1_width), (double *im2, int im2_height, int im2_width)}

%apply (float *INPLACE_ARRAY2, int DIM1, int DIM2) {(float *xflow, int xf_dim0, int xf_dim1), (float *yflow, int yf_dim0, int yf_dim1)}


%apply (double *IN_ARRAY2, int DIM1, int DIM2){(double *arr, int width, int height)} 

%include "gpu_motion.h"




