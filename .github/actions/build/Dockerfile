FROM debian:bookworm

ENV LANG=C LC_ALL=C DEBIAN_FRONTEND=noninteractive
RUN apt update --assume-yes && apt install --assume-yes -- python3

COPY run.py /sbin/run.py
RUN chmod +x /sbin/run.py

ENTRYPOINT ["/sbin/run.py"]
