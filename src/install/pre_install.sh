#!/usr/bin/env bash

# cd in this files directory for relative paths to work
cd "$( dirname "${BASH_SOURCE[0]}" )" || exit 1

FACTUSER=$(whoami)

CODENAME=$(lsb_release -cs)
if [ "${CODENAME}" = "ulyana" ]; then
    CODENAME=focal
elif [ "${CODENAME}" = "tara" ] || [ "${CODENAME}" = "tessa" ] || [ "${CODENAME}" = "tina" ]; then
    CODENAME=bionic
elif [ "${CODENAME}" = "rebecca" ] || [ "${CODENAME}" = "rafaela" ] || [ "${CODENAME}" = "rosa" ]; then
    CODENAME=trusty
    sudo apt-get -y install "linux-image-extra-$(uname -r)" linux-image-extra-virtual
elif  [ "${CODENAME}" = "kali-rolling" ]; then
    CODENAME=buster
elif [ -z "${CODENAME}" ]; then
	echo "Could not get Ubuntu codename. Please make sure that lsb-release is installed."
	exit 1
fi

echo "Install Pre-Install Requirements"
sudo apt-get -y install python3-pip git libffi-dev

# Install packages to allow apt to use a repository over HTTPS
sudo apt-get -y install apt-transport-https ca-certificates curl software-properties-common

echo "Installing Docker"

if [ "${CODENAME}" = "focal" ]
then
	sudo apt-get -y install docker-compose docker.io
else
	# Uninstall old versions
	sudo apt-get -y remove docker docker-engine docker.io
	
	if [ "${CODENAME}" = "stretch" ] || [ "${CODENAME}" = "buster" ]
	then
	    # Add Docker’s official GPG key
	    curl -fsSL https://download.docker.com/linux/debian/gpg | sudo apt-key add -
	
	    # set up the stable repository
	    if [ ! -f /etc/apt/sources.list.d/docker.list ]
	    then
	        echo "deb [arch=amd64] https://download.docker.com/linux/debian ${CODENAME} stable" > docker.list
	        sudo mv docker.list /etc/apt/sources.list.d/docker.list
	    fi
	else
	    # Add Docker’s official GPG key
	    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
	
	    # set up the stable repository
	    if  ! grep -q "^deb .*download.docker.com/linux/ubuntu" /etc/apt/sources.list /etc/apt/sources.list.d/*
	    then
	        sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $CODENAME stable"
	    fi
	fi
	# install docker
	sudo apt-get update
	sudo apt-get -y install docker-ce
fi

sudo systemctl enable docker

# add fact-user to docker group
if [ ! "$(getent group docker)" ]
then
    sudo groupadd docker
fi
sudo usermod -aG docker "$FACTUSER"

python3 -m pip install -U pip
python3 -m pip install -r ./requirements_pre_install.txt --prefer-binary

echo -e "Pre-Install-Routine complete! \\033[31mPlease reboot before running install.py\\033[0m"

exit 0
