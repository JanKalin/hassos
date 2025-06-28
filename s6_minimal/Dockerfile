ARG BUILD_FROM=ghcr.io/hassio-addons/base:13.2.0
FROM $BUILD_FROM

ENV LANG C.UTF-8

# Copy service run script to the correct s6 service directory
COPY run.sh /etc/services.d/s6_minimal/run
RUN chmod +x /etc/services.d/s6_minimal/run

