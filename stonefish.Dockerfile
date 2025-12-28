FROM ros:jazzy

RUN apt-get update && apt-get upgrade -y

RUN apt-get install -y git

RUN git clone https://github.com/patrykcieslak/stonefish

RUN apt-get install -y \
    libsdl2-dev \
    libglm-dev \
    libfreetype6-dev \
    ros-jazzy-pcl-conversions \
    ros-jazzy-image-transport 

RUN sed -i '30i#include <cstdint>' /stonefish/Library/include/sensors/Sample.h

RUN cd stonefish && \
    mkdir -p build && \
    cd build && cmake .. && \
    make -j4 && make install

WORKDIR /workspace
COPY . .
RUN rm -rf ./build ./log ./install
RUN /bin/bash -c "make"
CMD ["bash"]