FROM python:3.7-alpine

COPY . /opt/bigsql
WORKDIR /opt/bigsql
RUN pip3 install .

COPY ./tests /opt/tests
WORKDIR /opt/tests/

RUN pip3 install coverage

CMD coverage run test.py &> /dev/null && coverage report