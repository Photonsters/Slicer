# PhotonSlicer

The PhotonSlicer Converts STL (binary) files to Images or PhotonFile. It is programmed in Python 3 and uses Cython (fast compression / mesh calculations), OpenCV (image drawing routines), numpy (handling large image data) and pyopengl for slicing if possible.

---

## Status

Not yet ready:
- Real life test with the produced photon files have to be done.

---

## Installation

Download the repository. Depending on your setup do one of the following:

- **Windows**: 'Win64/' contains the 7Z files for Windows 64-bits returning your slicing progress in a window. Just unpack and run! If you want to have your progress info displayed as plain text, replace PhotonSlicer.exe with the file in Con64/.  
You can test your install with:
  `photonslicer.exe -s STLs\legocog.stl -g True -f False`

- **Linux/OSX**: For Linux and OSX you have to install python and some libraries (Cython, numpy, opencv-python, PyOpenGL, PyOpenGL-accelerate, Pygame if glut not available). To test it:
  `python3 photonslicer.py -s STLs\legocog.stl -g True -f False`

- **Linux & MeshMixer**: First make sure you already have Wine installed and use it to run MeshMixer 3.3. You should unpack the 'Win64/' 7Z files from the repository to e.g. 'Program Files'. You can test your it with:
  `wine photonslicer.exe -s STLs\legocog.stl -g True -f False`

---

## Setup MeshMixer
1. Install MeshMixer (Linux users: First install Wine and install MeshMixer in Wine)
2. Download and unpack the zips in /Win64 (use 7-zip) to a location on your computer e.g. C:/Program Files/PhotonSlicer/
3. Open MeshMixer
4. Go to menu File > Preferences (Alt-T)
5. Go to tab Printers
6. Choose Add
7. Fill fields as follows:
    - Manufacturer: 'Anycubic'
    - Model: 'Photon - MC Rapid Clear' or append your own resin brand/type names
    - Width: '65.00'
    - Depth: '115.00'
    - Height: '155.00'
    - Printer software name : 'Photon Slicer'
    - Printer software path : 'C:/Program Files/PhotonSlicer/PhotonSlicer.exe'
    - Format of file to ... : 'STL'
    - Command line artuments: '-g True -f False -e folder -l 0.05 -o 6 -t 8 -be 90 -bl 8 -p "C:/Program Files/PhotonSlicer/STLs/photon" -s'      
8. Close window 'Printer Properties'
9. Close window 'Preferences'

You can add an extra 'printer' for each resin / settings combo you need.


## Use MeshMixer to Slice
1. Open an STL file, check if fits the build volume and is not below it.
2. Press 'Print' icon on bottom of left toolbar.
3. A progress windows appears.
4. The folder with your photon file opens

If you don't see a progress window and now file is added to 'C:/Program Files/PhotonSlicer/STLs/photon' check 'C:/Program Files/PhotonSlicer/log.txt' for error messages.


## MeshMixer Full Workflow

1. Open an STL file, check if fits the build volume and is not below it.
2. Hollow in MeshMixer
    - The Hot End - https://www.youtube.com/watch?v=dC_nPqJFQbY
    - Model3D - https://www.youtube.com/watch?v=ZXu6VYj4Um0
3. Infill in MeshMixer
    - Maker's Muse - https://www.youtube.com/watch?v=ffmg1E3m1Ak&t=375s
4. Orientation - Principles using Anycubic Photon Slicer
    - All About 3D Blog - https://www.youtube.com/watch?v=7eZWHUOhoAw
5. Supports in MeshMixer
    - MeshMixer - https://www.youtube.com/watch?v=aFTyTV3wwsE
    - Josef Prusa - FDM: https://www.youtube.com/watch?v=OXFKVmMwXCQ
6. Press 'Print' icon on bottom of left toolbar. A progress windows appears.
7. The folder with your photon file opens

---

## Functionality under development
- The main focus will remain speed, although OpenGL slicing made it a lot faster.
- Since PhotonSlicer was mainly meant as a plugin, mesh editing (hollowing/infill/positioning) will not be developed. Use the functionality of MeshMixer instead!

---

## Command Line Parameters
```
usage: PhotonSlicer.py [-h] -s FILENAME [-p PHOTONFILENAME]
                       [-r RESCALE]
                       [-l LAYERHEIGHT] [-t EXPOSURE] [-be BOTTOMEXPOSURE]
                       [-bl BOTTOMLAYERS] [-o OFFTIME]
                       [-g GUI] [-f FORCECPU]
                       [-e EXECUTE]

required: stlfilename

examples: PhotonSlicer.exe -s ./STLs/Cube.stl                         -> ./STLs/Cube.photon
          PhotonSlicer.exe -s ./STLs/Cube.svg                         -> ./STLs/Cube.photon
          PhotonSlicer.exe -s ./STLs/Cube.stl -p photon -l 0.05       -> ./STLs/Cube.photon
          PhotonSlicer.exe -s ./STLs/Cube.stl -p /home/photon -l 0.05 -> /home/Cube.photon
          PhotonSlicer.exe -s ./STLs/Cube.stl -p /Sqrs.photon -l 0.05 -> /Sqrs.photon
          PhotonSlicer.exe -s ./STLs/Cube.stl -p images -l 0.05    -> ./STLs/Cube/0001.png,..
          PhotonSlicer.exe -s ./STLs/Cube.stl -p ./sliced/ -l 0.05 -> ./sliced/0001.png,..
          PhotonSlicer.exe -s dialog -p dialog -g True -f False    -> OpenGL is used

optional arguments:
  -h, --help            show this help message and exit
  -s STLFILENAME, --stlfilename STLFILENAME
                        name of (binary) stl file to import
  -p PHOTONFILENAME, --photonfilename PHOTONFILENAME
                        photon file name (ends with '.photon') OR
                        output directory (ends with '/') for images OR
                        'dialog' to select photon file (only in GUI mode) OR
                        'dialogdir' to select dir to save images (only in GUI mode) OR
                        'photon' as argument to generate photon file with same name OR
                        'images' to generate images in directory with same name as stl
                        these can be combined e.g. './subdir/photon'
  -l LAYERHEIGHT, --layerheight LAYERHEIGHT
                        layer height in mm
  -r RESCALE, --rescale RESCALE
                        scales model and offset
  -t EXPOSURE, --exposure EXPOSURE
                        normal exposure time (sec)
  -be BOTTOMEXPOSURE, --bottomexposure BOTTOMEXPOSURE
                        exposure time for bottom layers
  -bl BOTTOMLAYERS, --bottomlayers BOTTOMLAYERS
                        nr of layers with exposure for bottom
  -o OFFTIME, --offtime OFFTIME
                        off time between layers (sec)
  -g GUI, --gui GUI     show progress in popup window
  -f FORCECPU, --forceCPU FORCECPU
                        force slicing with CPU instead of GPU/OpenGL
  -e EXECUTE, --execute EXECUTE
                        execute command when done
                        'photon' will be replace with output filename
                        if argument is 'folder' a file browser will open

```
