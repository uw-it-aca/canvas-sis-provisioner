#!/bin/bash

if [ -f /tmp/apache2-local.conf ]
then

  cat /tmp/apache2-local.conf >> /etc/apache2/apache2.conf

fi
