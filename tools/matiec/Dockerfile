# MatIEC: the IEC 61131-3 -> C compiler used by OpenPLC.
# Used by PLCGuard to check that dataset programs and LLM repairs are valid ST.
FROM debian:bookworm-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential bison flex autoconf automake git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
# Pinned commit of https://github.com/beremiz/matiec for reproducibility.
ARG MATIEC_COMMIT=c316fe57e335381cbe91f61c7366857198580ac7
RUN git clone https://github.com/beremiz/matiec /matiec \
    && cd /matiec && git checkout ${MATIEC_COMMIT} \
    && autoreconf -i && ./configure && make -j"$(nproc)"

FROM debian:bookworm-slim
COPY --from=build /matiec/iec2c /usr/local/bin/iec2c
COPY --from=build /matiec/lib /opt/matiec/lib
WORKDIR /src
# Usage: docker run --rm -v "$PWD:/src" plcguard-matiec <file.st>
ENTRYPOINT ["iec2c", "-I", "/opt/matiec/lib", "-T", "/tmp"]
