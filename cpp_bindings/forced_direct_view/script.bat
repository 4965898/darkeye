chcp 65001
REM 请在官方的vs 2022 Tool下运行，在CMakeLists.txt所在的文件夹下运行
if exist build rd /s /q build
mkdir build
cd build
call conda activate avlite2

cmake -S .. -G Ninja -DCMAKE_BUILD_TYPE=Release -DShiboken6_DIR="C:/Users/yin/anaconda3/envs/avlite2/Lib/site-packages/Shiboken6/lib/cmake/Shiboken6" -DPySide6_DIR="C:/Users/yin/anaconda3/envs/avlite2/Lib/site-packages/PySide6/cmake/PySide6" -DCMAKE_PREFIX_PATH="E:\Qt\6.10.1\msvc2022_64\lib\cmake"
ninja
ninja install
cd ..