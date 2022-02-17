FROM nvidia/cuda:11.4.2-cudnn8-runtime-ubuntu20.04

ENV HF_DATASETS_CACHE="/datasets/cached"
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Los_Angeles
ENV NCCL_DEBUG=INFO
RUN apt update && \
    apt install -y bash \
                   build-essential \
                   git \
                   curl \
                   ca-certificates \
                   python3 \
                   expect \
                   python3-pip \
                   vim

RUN python3 -m pip install --no-cache-dir --upgrade pip && \
    python3 -m pip install --no-cache-dir \
    transformers \
    tokenizers \
    datasets \
    sklearn \
    torch


RUN git clone https://github.com/NVIDIA/apex
RUN cd apex && \
    python3 setup.py install && \
    pip install -v --no-cache-dir --global-option="--cpp_ext" --global-option="--cuda_ext" ./

WORKDIR /workspace
COPY . transformers/
RUN cd transformers/ &&
    python3 -m pip install --no-cache-dir .

CMD ["/bin/bash"]