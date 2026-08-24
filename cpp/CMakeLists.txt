cmake_minimum_required(VERSION 3.16)
project(xPatch VERSION 0.1.25 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt6 COMPONENTS Core Gui Widgets REQUIRED)

add_executable(xPatch
    src/main.cpp
    src/MainWindow.cpp
    src/XDeltaRunner.cpp
    src/utils/Paths.cpp
    src/utils/Files.cpp
    src/utils/Checksum.cpp
    resources/resources.qrc
)

target_include_directories(xPatch PRIVATE src)
target_link_libraries(xPatch PRIVATE Qt6::Core Qt6::Gui Qt6::Widgets)

set_target_properties(xPatch PROPERTIES
    OUTPUT_NAME "xPatch"
    MACOSX_BUNDLE TRUE
    WIN32_EXECUTABLE TRUE
)