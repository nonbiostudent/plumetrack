#include "gpu_motion.h"

bool haveGPU(void){
	//Returns true if there is at least one CUDA capable GPU detected on this
	//system.
	int n;
	cudaError_t ret_code = cudaGetDeviceCount(&n);
	return ((ret_code == cudaSuccess) && (n > 0));

}


GPUInterface::GPUInterface(double scale, int numLevels, int winSize, int numIters,
                           int polyN, double polySigma){

	farneback_engine.pyrScale = scale;
	farneback_engine.numLevels = numLevels;
	farneback_engine.winSize = winSize;
	farneback_engine.numIters= numIters;
	farneback_engine.polyN = polyN;
	farneback_engine.polySigma = polySigma;
	farneback_engine.flags = cv::OPTFLOW_FARNEBACK_GAUSSIAN;

}

GPUInterface::~GPUInterface(){};



int GPUInterface::computeFlow(double *im1, int im1_height, int im1_width, double *im2,
		           int im2_height, int im2_width, float *xflow, int xf_dim0,
		           int xf_dim1, float *yflow, int yf_dim0, int yf_dim1){

	//check dimensions
	if ((im1_width != im2_width) || (im2_width != xf_dim1)){
		ERROR("Images and/or flow array have different widths (%d, %d and %d)",
				im1_width, im2_width, xf_dim1);
		return 1;
	}

	if ((im1_height != im2_height) || (im2_height != xf_dim0)){
		ERROR("Images and/or flow array have different heights (%d, %d and %d)",
			  im1_height, im2_height, xf_dim0);
		return 1;
	}

	if ((xf_dim0 != yf_dim0) || (xf_dim1 != yf_dim1)){
		ERROR("xflow and yflow arrays must be the same size.");
		return 1;
	}

	cv::Mat im1_host_mat(im1_height, im1_width, CV_64FC1, im1);
	cv::Mat im2_host_mat(im2_height, im2_width, CV_64FC1, im2);
	cv::Mat xflow_host_mat(im1_height, im1_width, CV_32FC1, xflow);
	cv::Mat yflow_host_mat(im1_height, im1_width, CV_32FC1, yflow);

	//transfer the image data onto the GPU
	im1_device_mat.upload(im1_host_mat);
	im2_device_mat.upload(im2_host_mat);


	//do the motion estimation
	farneback_engine(im1_device_mat, im2_device_mat, xflow_device_mat,
			         yflow_device_mat);

	//get the results from the GPU
	xflow_device_mat.download(xflow_host_mat);
	yflow_device_mat.download(yflow_host_mat);

	return 0;

}

