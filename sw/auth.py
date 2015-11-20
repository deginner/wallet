import os
import base64
import random
import logging

import bitjws
from flask import Response, current_app, g
from flask.ext.login import UserMixin

from . import database as db
from .error import Errors

TOTP_ISSUER = 'Deglet'


class User(UserMixin):
    def __init__(self, id, username, address):
        self.id = id
        self.username = username
        self.address = address

    def __str__(self):
        return '<User {}: {} {}>'.format(self.username, self.address, self.id)


def authenticate(request):
    """
    Authenticate user based on the JWS message received. If it succeeds,
    then g.payload will contain the decoded JWS payload. If it fails,
    then g.auth_err contains a Response encoded in JWS signed by this
    server.
    """
    resp = jws_preprocessor(request, 401)
    if isinstance(resp, Response):
        # Validation failed.
        g.auth_err = resp
        return None

    # Store the decoded payload so it can be used for processing the request.
    g.payload = resp['data']

    publickey = resp['header']['kid'].encode('ascii')
    userkey = current_app.session.query(db.UserKey).filter(
        db.UserKey.key == publickey).one_or_none()
    if userkey is None:
        # No user found.
        logging.error("No user found for key {}".format(publickey))
        g.auth_err = current_app.encode_error(Errors.UserNotFound, 401)
        return None

    # Check last nonce used.
    nonce = int(resp['data'].get('iat', 0))
    if nonce <= userkey.last_nonce:
        logging.error("Nonce {} is not greater than the last one {}".format(
            nonce, userkey.last_nonce))
        g.auth_err = current_app.encode_error(Errors.InvalidNonce, 401)
        return None

    # Update last nonce.
    userkey.last_nonce = nonce
    current_app.session.add(userkey)
    current_app.session.commit()

    return User(userkey.user.id, userkey.user.username, publickey)


def unauthorized():
    if hasattr(g, 'auth_err'):
        # auth_err is set by the authenticate function in case
        # the request cannot be authenticated.
        return g.auth_err
    else:
        return Response("not authorized", status=401)


def jws_preprocessor(request, status=400):
    """Deserialize the JWS received in the request."""
    url = request.base_url
    data = request.data.encode('utf8')

    try:
        header, payload = bitjws.validate_deserialize(data, requrl=url)
    except Exception:
        logging.exception("Failed to validate and deserialize message")
        return current_app.encode_error(Errors.InvalidMessage, status)

    if header is None or payload is None:
        logging.error("Signature validation failed")
        return current_app.encode_error(Errors.InvalidSignature, status)

    return {'header': header, 'data': payload}


def gen_totp_sharedsecret():
    raw = os.urandom(10)
    key = base64.b32encode(raw)
    return key


def gen_totp_uri(username, secret):
    uri = 'optauth://totp/{label}?secret={secret}&issuer={issuer}'
    return uri.format(
        label='{} - {}'.format(username, TOTP_ISSUER),
        secret=secret,
        issuer=TOTP_ISSUER)


def gen_tfa_resetcodes():
    r = random.SystemRandom()
    codes = [str(r.randint(0, 1e6)).zfill(6) for _ in range(4)]
    return ','.join(codes)
