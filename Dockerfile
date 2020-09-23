FROM acait/django-container:1.1.3 as app-container

USER root
RUN apt-get update && apt-get install mysql-client libmysqlclient-dev -y
RUN chgrp acait /etc/apache2/apache2.conf
RUN chmod g+w /etc/apache2/apache2.conf
USER acait

ADD --chown=acait:acait sis_provisioner/VERSION /app/sis_provisioner/
ADD --chown=acait:acait setup.py /app/
ADD --chown=acait:acait requirements.txt /app/
RUN . /app/bin/activate && pip install -r requirements.txt

RUN . /app/bin/activate && pip install mysqlclient

ADD --chown=acait:acait . /app/
ADD --chown=acait:acait docker/ project/
ADD --chown=acait:acait docker/apache2.conf /tmp/apache2-local.conf
ADD --chown=acait:acait docker/app_start.sh /scripts
RUN chmod u+x /scripts/app_start.sh

RUN . /app/bin/activate && pip install nodeenv && nodeenv -p &&\
    npm install -g npm && ./bin/npm install less -g

RUN . /app/bin/activate && python manage.py collectstatic --noinput &&\
    python manage.py compress -f

FROM acait/django-test-container:1.1.3 as app-test-container

COPY --from=0 /app/ /app/
COPY --from=0 /static/ /static/
