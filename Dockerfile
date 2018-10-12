FROM uucin/python:3.7-alpine
 
ADD . /app
WORKDIR /app
 
ENV PYPI_SERVER https://pypi.douban.com/simple
 
RUN pip3 install pip setuptools --upgrade -i $PYPI_SERVER \
    && pip3 install -r /app/requirements.txt -i $PYPI_SERVER

CMD ["python3", "run_dnskey.py", "-b", ":::17000"]
