#!/bin/bash

# if [ -e doc/ ]; then rm -rf doc/; fi
./epydoc.tripu -odoc/ -n"Instalador «live» de Guadalinex 2005" ./*
sed s/public/private/ doc/index.html > /tmp/$0.tmp
mv /tmp/$0.tmp doc/index.html

