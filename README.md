## Pre-requisities

```
apt-get install autoconf libtool libkrb5-dev haproxy
```

#### MongoDB

If you have issues running these instructions, visit
https://docs.mongodb.org/manual/tutorial/install-mongodb-on-ubuntu/

Installation steps:

```
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 7F0CEB10
echo "deb http://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/3.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-3.0.list
sudo apt-get update
sudo apt-get install mongodb-org
```

Starting MongoDB:

```
sudo service mongod start
```


#### libsecp256k1

Installation steps:

```
git clone git://github.com/bitcoin/secp256k1.git libsecp256k1
cd libsecp256k1
git checkout d7eb1ae96dfe9d497a26b3e7ff8b6f58e61e400a
./autogen.sh
./configure --enable-module-recovery
make
sudo make install
sudo ldconfig
```


## Installing deglet-server

```
git clone https://github.com/g-p-g/wallet
cd wallet
make setup
```

Set `api_signing_key` at `config/default.json` to a private key in WIF format.

#### Running deglet-server

```
supervisord
```
