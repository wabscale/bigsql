FROM python:3.7-alpine

RUN apk add --update --no-cache mysql-client

WORKDIR /opt/tests/
COPY ./requirements.txt ./requirements.txt
RUN pip3 install -r requirements.txt && pip3 install coverage

COPY . .

RUN cp tests/test.py test.py

CMD echo "waiting for db" \
  && while ! mysqladmin ping -h "db" -P "3306" --silent; do sleep 1; done \
  && sleep 3 \
  && coverage run test.py \
  && coverage report
