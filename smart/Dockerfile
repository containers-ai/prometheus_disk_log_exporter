FROM python:2.7-alpine

COPY ["smart_exporter", "/root/smart_exporter"]
COPY ["requirements.txt", "/root/requirements.txt"]

WORKDIR /root

#RUN groupadd -g 999 appuser && \
#    useradd -r -u 999 -g appuser appuser
RUN apk add --no-cache smartmontools
RUN pip install -r requirements.txt
RUN chmod -R 755 ./ 

#RUN addgroup -S appgroup && adduser -S appuser -G appgroup
RUN chmod 777 /usr/sbin/smartctl

#USER appuser
#USER root


ENTRYPOINT ["python", "smart_exporter/__main__.py"]
CMD [""]
EXPOSE 9110
