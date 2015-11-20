SHELL=/bin/bash -O extglob

clean:
	rm -rf -- *.egg *.egg-info build/ dist/ **/*.pyc **/__pycache__

setup:
	mkdir -p service/log
	cp -u config/default.json.orig config/default.json
	cp -u config/gunicorn.conf.py.orig config/gunicorn.conf.py
	python setup.py install
	cd js && rm -rf bitcore-wallet-service &&\
		npm install && mv node_modules/bitcore-wallet-service .

sql_setup:
	python sw/database.py
