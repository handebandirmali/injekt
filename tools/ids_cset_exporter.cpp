#include <iostream>
#include <string>
#include <vector>
#include <cstdlib>

#include "ids_peak_comfort_c/ids_peak_comfort_c.h"

static void print_usage()
{
    std::cout << "Usage:\n";
    std::cout << "  ids_cset_exporter.exe --index <camera_index> --out <output_path>\n";
}

int main(int argc, char* argv[])
{
    int camIndex = -1;
    std::string outPath;

    for (int i = 1; i < argc; ++i)
    {
        std::string arg = argv[i];
        if (arg == "--index" && i + 1 < argc)
        {
            camIndex = std::atoi(argv[++i]);
        }
        else if (arg == "--out" && i + 1 < argc)
        {
            outPath = argv[++i];
        }
    }

    if (camIndex < 0 || outPath.empty())
    {
        print_usage();
        return 2;
    }

    peak_status status = PEAK_STATUS_SUCCESS;
    peak_camera_handle hCam = nullptr;

    status = peak_Library_Init();
    if (status != PEAK_STATUS_SUCCESS)
    {
        std::cerr << "peak_Library_Init failed: " << status << "\n";
        return 10;
    }

    try
    {
        size_t cameraCount = 0;

        status = peak_CameraList_Update(nullptr);
        if (status != PEAK_STATUS_SUCCESS)
        {
            std::cerr << "peak_CameraList_Update failed: " << status << "\n";
            peak_Library_Exit();
            return 11;
        }

        status = peak_CameraList_Get(nullptr, &cameraCount);
        if (status != PEAK_STATUS_SUCCESS)
        {
            std::cerr << "peak_CameraList_Get(count) failed: " << status << "\n";
            peak_Library_Exit();
            return 12;
        }

        if (cameraCount == 0)
        {
            std::cerr << "No IDS cameras found.\n";
            peak_Library_Exit();
            return 13;
        }

        if (camIndex >= static_cast<int>(cameraCount))
        {
            std::cerr << "Camera index out of range. Found " << cameraCount << " camera(s).\n";
            peak_Library_Exit();
            return 14;
        }

        std::vector<peak_camera_descriptor> cameras(cameraCount);

        status = peak_CameraList_Get(cameras.data(), &cameraCount);
        if (status != PEAK_STATUS_SUCCESS)
        {
            std::cerr << "peak_CameraList_Get(list) failed: " << status << "\n";
            peak_Library_Exit();
            return 15;
        }

        status = peak_Camera_Open(cameras[camIndex].cameraID, &hCam);
        if (status != PEAK_STATUS_SUCCESS || hCam == nullptr)
        {
            std::cerr << "peak_Camera_Open failed: " << status << "\n";
            peak_Library_Exit();
            return 16;
        }

        status = peak_CameraSettings_DiskFile_Store(hCam, outPath.c_str());
        if (status != PEAK_STATUS_SUCCESS)
        {
            std::cerr << "peak_CameraSettings_DiskFile_Store failed: " << status << "\n";
            peak_Camera_Close(hCam);
            peak_Library_Exit();
            return 17;
        }

        std::cout << "CSET exported successfully: " << outPath << "\n";

        peak_Camera_Close(hCam);
        peak_Library_Exit();
        return 0;
    }
    catch (...)
    {
        if (hCam)
        {
            peak_Camera_Close(hCam);
        }
        peak_Library_Exit();
        std::cerr << "Unexpected native exception.\n";
        return 99;
    }
}