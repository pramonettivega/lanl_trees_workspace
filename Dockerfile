FROM quay.io/jupyter/base-notebook:latest

USER root

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gfortran \
    make \
    cmake \
    build-essential \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp
RUN git clone https://github.com/lanl/Trees.git

WORKDIR /tmp/Trees

RUN sed -i 's/metryc\.F90/metryc.f90/g' CMakeLists.txt && \
    sed -i 's/shapes\.F90/shapes.f90/g' CMakeLists.txt && \
    sed -i 's/VarRoutines_DUET\.F90/VarRoutines_DUET.f90/g' ModularDUET/CMakeLists.txt && \
    sed -i 's/Out_DUET\.F90/Out_DUET.f90/g' ModularDUET/CMakeLists.txt && \
    sed -i 's/support_DUET\.F90/support_DUET.f90/g' ModularDUET/CMakeLists.txt

RUN mkdir -p build && \
    cd build && \
    cmake .. && \
    make -j"$(nproc)"

RUN pip install --no-cache-dir \
    geopandas \
    rasterio \
    scipy

RUN cp /tmp/Trees/build/trees.exe /home/jovyan/work/trees.exe && \
    rm -rf /tmp/Trees && \
    chown -R ${NB_UID}:${NB_GID} /home/jovyan/work && \
    find /home/jovyan/work -type d -exec chmod 775 {} \; && \
    find /home/jovyan/work -type f -exec chmod 664 {} \; && \
    chmod 755 /home/jovyan/work/trees.exe

USER ${NB_UID}
WORKDIR /home/jovyan/work