import os
import time
import json
import logging

import requests
from flask import Flask, Response, request
from flask.ext.cors import CORS
from flask.ext.login import LoginManager
import bitjws

from . import auth
from . import database
from .handler import user, serverwallet

logger = logging.getLogger("")
logger.setLevel(logging.DEBUG)

ENVCFG = 'DEGLET_CONFIG'


class Application(Flask):
    def __init__(self, config=None):
        super(Application, self).__init__(__name__)
        self._privkey = None
        self._dbcfg = None
        self._cosigner_server = None
        self._load_config(config)
        self._setup_auth()
        self._setup_api()

        self.teardown_appcontext(self._shutdown_session)

        CORS(self)

    def encode_success(self, obj=None):
        """Encode a successful message in JWS."""
        signed = self._sign(obj)
        return Response(signed)

    def encode_error(self, err, code=400):
        """Encode error messages in JWS."""
        obj = {'error': err.reason, 'code': err.code}
        signed = self._sign(obj)
        return Response(signed, status=code)

    def cosigner(self, path, **kwargs):
        """Communicate with the cosigner server."""
        if self._cosigner_server is None:
            return None

        res = requests.post(
            self._cosigner_server + path,
            data=json.dumps(kwargs),
            headers={'Content-Type': 'application/json'})
        content = res.json()
        return content

    def _sign(self, obj):
        iat = time.time()
        audience = request.base_url
        signed = bitjws.sign_serialize(
            self._privkey, requrl=audience, iat=iat, data=obj)
        return signed

    def _load_config(self, config):
        if ENVCFG in os.environ:
            logging.info("Loading config from {}".format(ENVCFG))
            #self.config.from_envvar(ENVCFG)
            data = json.load(open(os.getenv(ENVCFG)))
            self.config.update(**data)
        else:
            logging.warn("{} not defined".format(ENVCFG))
        if isinstance(config, dict):
            self.config.update(**config)

        if not self.config.get('api_signing_key'):
            raise Exception("Invalid config: missing api_signing_key")
        # Server key used to sign responses. The client can optionally
        # check that the response was signed by a key it knows to belong
        # to this server.
        self._privkey = bitjws.PrivateKey(
            bitjws.wif_to_privkey(self.config['api_signing_key']))
        logging.info("Server key address: {}".format(
            bitjws.pubkey_to_addr(self._privkey.pubkey.serialize())))

        self._cosigner_server = self.config.get('cosigner_server')
        if not self._cosigner_server:
            logging.warning("cosigner_server not present in config, "
                            "cosigning will not be available.")

        self._dbcfg = self.config.get('api_database')
        if not self._dbcfg:
            raise Exception("Invalid config: missing api_database")
        if 'engine' not in self._dbcfg:
            raise Exception("Invalid config for api_databae: missing 'engine'")

    def _setup_auth(self):
        manager = LoginManager()
        manager.init_app(self)
        manager.request_loader(auth.authenticate)
        manager.unauthorized_handler(auth.unauthorized)

    def _setup_api(self):
        engine = database.setup_engine(**self._dbcfg['engine'])
        session_factory = database.session_factory(
            engine, **self._dbcfg.get('session', {}))
        # This is a scopped session, so each request handler will create
        # and destroy them as necessary.
        self.session = database.get_session(session_factory)

        self.register_blueprint(user.blueprint)
        self.register_blueprint(serverwallet.blueprint)

    def _shutdown_session(self, exception=None):
        if exception:
            logging.error(exception)
        # Cleanup the session instance used in this last request.
        self.session.remove()
