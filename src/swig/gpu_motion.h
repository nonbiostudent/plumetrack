

#ifndef __GPU_MOTION_H
#define __GPU_MOTION_H
#include "traceback.h"
#include "cuda_runtime.h"
#include "opencv2/opencv.hpp"
#include "opencv2/gpu/gpu.hpp"


class GPUInterface{
	public:
		GPUInterface(double scale, int numLevels, int winSize, int numIters,
                     int polyN, double polySigma);

		~GPUInterface();


		int computeFlow(double *im1, int im1_height, int im1_width, double *im2,
		                int im2_height, int im2_width, float *xflow, int xf_dim0,
		                int xf_dim1, float *yflow, int yf_dim0, int yf_dim1);

		int testArray(double *arr, int width, int height);

	private:
		cv::gpu::FarnebackOpticalFlow farneback_engine;
		cv::gpu::GpuMat im1_device_mat, im2_device_mat, xflow_device_mat, yflow_device_mat;

};


bool haveGPU(void);


#endif //__GPU_MOTION_H
