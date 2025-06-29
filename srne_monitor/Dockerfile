ARG BUILD_FROM
FROM ${BUILD_FROM}

# Add requirements
ENV LANG C.UTF-8

RUN apk add --no-cache bash python3 py3-pip py3-paho-mqtt py3-pyserial

COPY run.sh /run.sh
COPY srne_monitor.py /srne_monitor.py
COPY pymodbus/ /pymodbus/

RUN chmod a+x /run.sh /srne_monitor.py

CMD [ "/run.sh" ]

