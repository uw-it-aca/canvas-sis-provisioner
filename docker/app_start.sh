#!/bin/bash

if [ "$ENV"  = "localdev" ]
then

  python manage.py migrate

fi
