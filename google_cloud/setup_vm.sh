#!/bin/bash

# This script sets up the required packages within Compute Instance VMs
# instantiated from Tensorflow Deep Learning template to run the firecam
# wildifre detection software.
# This script resides in firecam github repo itself, so its expected that
# firecam repo has already been git cloned into directory /root/firecam
# and that this script is run as root user.  E.g.
# sudo su -
# git clone https://github.com/fuego-dev/firecam.git
# bash firecam/google_cloud/setup_vm.sh

# install packages
apt-get update
apt-get -y install libpq-dev
apt-get -y install sqlite3
pip3 install -U pip
pip3 install -U psycopg2
pip3 install -U twilio
pip3 install -U numpy
pip3 install -U scipy
pip3 install -U docker


# change timezone
ln -fs /usr/share/zoneinfo/America/Los_Angeles /etc/localtime
dpkg-reconfigure -f noninteractive tzdata

# prefetch inference server docker image
docker pull gcr.io/dkgu-dev/inception:latest

# copy config files for firecam repo from cloud storage
# It is expected that fuego-firecam-configs bucket contains a top level filed
# named 'latest' that contains the directory name with settings.py, token.json,
# credentials.json, output_labels.txt, and the frozen .pb model file.
latest=`gsutil cat gs://fuego-firecam-configs/latest`
gsutil cp gs://fuego-firecam-configs/${latest}/settings.py /root/firecam
mkdir /root/keys
gsutil cp gs://fuego-firecam-configs/${latest}/token.json /root/keys
gsutil cp gs://fuego-firecam-configs/${latest}/credentials.json /root/keys
mkdir /root/models
gsutil cp gs://fuego-firecam-configs/${latest}/output_labels.txt /root/models
model=`gsutil ls gs://fuego-firecam-configs/${latest} | grep frozen_`
gsutil cp $model /root/models

# copy systemd service config file to systemd directory, so the detection code
# can be started with 'systemctl start firecam_detect'
cp firecam/google_cloud/firecam_detect.service /etc/systemd/system/
