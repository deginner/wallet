"""
Handles user creation and data retrieval for existing users.
"""

import logging

from flask import Blueprint, Response, request, current_app, g
from flask.ext.restful import Api, Resource
from flask.ext.login import login_required, current_user

from .. import database as db
from ..util import entropy
from ..auth import jws_preprocessor
from ..error import ErrorCode, Errors
from ..constant import (MIN_ITERCOUNT, MIN_SALTENTROPY,
                        MAX_USERNAMELEN, MAX_BLOBLEN, MAX_BLOBCOUNT)


def signup_request(header, data):
    """Handle a signup request."""
    address = header['kid']
    lastnonce = data['iat']

    username = data['username'].encode('utf8')
    usercheck = data['check'].encode('ascii')
    salt = data['salt'].encode('ascii')
    itercount = int(data['iterations'])

    if len(username) > MAX_USERNAMELEN:
        return Errors.UsernameTooLong
    elif itercount < MIN_ITERCOUNT:
        return Errors.LowIterCount
    elif entropy(salt) < MIN_SALTENTROPY:
        logging.debug('salt entropy {} < {}  ({})'.format(
            entropy(salt), MIN_SALTENTROPY, salt))
        return Errors.BadSalt
    elif lastnonce < 0:
        return Errors.InvalidNonce

    newuser = db.User(salt=salt, username=username,
                      user_check=usercheck, itercount=itercount)
    # Create a new UserKey that links back to the User above.
    newkey = db.UserKey(user=newuser, key=address,
                        last_nonce=lastnonce,
                        key_type=db.KeyType.publickey.name)

    return [newuser, newkey]


def signup_insert(records):
    session = current_app.session
    session.add_all(records)
    try:
        session.commit()
        return current_app.encode_success()
    except Exception as err:
        logging.exception("Failed to commit user records")
        session.rollback()

        if (isinstance(err, db.IntegrityError)
                and 'username' in err.orig.message):
            # Username already in use
            resp = current_app.encode_error(Errors.InvalidUsername)
        else:
            resp = current_app.encode_error(Errors.GenericError)

        return resp
    finally:
        session.close()


def format_blob(*blobs):
    for b in blobs:
        yield {
            'id': b.id,
            'blob': b.blob,
            # Convert datetime to unix timestamp.
            'created_at': int(b.created_at.strftime('%s'))
        }


class UserSignup(Resource):

    def post(self):
        """
        Register a new user.

        Parameters required from the client:
            * username   [text]
            * check      [text]    - 6 hexadecimal digits
            * salt       [text]    - hexadecimal digits
            * iterations [integer] - must be at least 10000
        """
        resp = jws_preprocessor(request)
        if isinstance(resp, Response):
            # Some error occurred.
            return resp

        records = signup_request(**resp)
        if isinstance(records, ErrorCode):
            logging.error("Failed to validate signup request")
            err = records
            return current_app.encode_error(err)

        return signup_insert(records)


class UserData(Resource):

    def get(self):
        """
        Return the salt and iteration count (for PBKDF2) for this user.

        Parameters required from the client:
            * username [text]
            * check    [text] - 6 hexadecimal digits

        Returns:
            * salt       [text]   - hexadecimal digits
            * iterations [integer]
        """
        username = request.args.get('username').encode('utf8')
        bcheck = request.args.get('check').encode('ascii')
        if not username or len(bcheck) != 6:
            return current_app.encode_error(Errors.MissingArguments)

        user = current_app.session.query(db.User).filter(
            db.User.username == username,
            db.User.user_check == bcheck).one_or_none()
        if user is None:
            return current_app.encode_error(Errors.UserNotFound)

        result = {'salt': user.salt, 'iterations': user.itercount}
        return current_app.encode_success(result)


class UserStoreBlob(Resource):

    @login_required
    def post(self):
        # XXX blob update not implemented yet.
        """
        Store or update a blob for this user.

        Parameters required from the client:
            * id [text]   - an UUID (assumed to be a wallet ID)
            * blob [text] - blob to be stored

        Optional parameters:
            * maxchanges [integer] - maximum number of changes accepted for
                                     this blob, no more than 32

        Returns:
            * id [text]            - id for the blob stored
            * blob [text]          - the blob stored
            * created_at [integer] - creation time as a unix timestamp
        """
        maxchanges = min(int(g.payload.get('maxchanges', '32')), 32)
        blob = g.payload.get('blob', '').encode('ascii')
        # Blob ID is used internally as a reference to the Wallet record
        # stored in the MongoDB by bitcore-wallet-service.
        # The default client implementation passes that UUID as this id,
        # but it is not enforced.
        blob_id = g.payload.get('id', '').encode('ascii')

        if not blob or not blob_id or len(blob_id) != 36:
            # No blob specified.
            return current_app.encode_error(Errors.MissingArguments)
        elif len(blob) > MAX_BLOBLEN:
            # Blob size is too big.
            return current_app.encode_error(Errors.BlobTooLong)

        blob_count = current_app.session.query(db.WalletBlob).filter(
            db.WalletBlob.user_id == current_user.id).count()
        if blob_count >= MAX_BLOBCOUNT:
            # This user has stored too many blobs already.
            return current_app.encode_error(Errors.TooManyBlobs)

        record = db.WalletBlob(id=blob_id, user_id=current_user.id,
                               updates_left=maxchanges, blob=blob)
        current_app.session.add(record)
        current_app.session.commit()

        result = format_blob(record).next()
        return current_app.encode_success(result)

    @login_required
    def put(self):
        # XXX not implemented in the client yet.
        """
        Update an existing blob for this user.

        Parameters required from the client:
            * id [text]   - blob UUID
            * blob [text] - blob to replace the one previously stored

        Returns:
            the new blob
        """
        blob = g.payload.get('blob', '').encode('ascii')
        blob_id = g.payload.get('id', '').encode('ascii')
        if not blob or not blob_id:
            # No blob specified.
            return current_app.encode_error(Errors.MissingArguments)
        elif len(blob) > MAX_BLOBLEN:
            # Blob size is too big.
            return current_app.encode_error(Errors.BlobTooLong)

        # Update the blob that belongs to this user only if this new one
        # is greater (in size) than the current one.
        record = current_app.session.query(db.WalletBlob).filter(
            db.WalletBlob.user_id == current_user.id,
            db.WalletBlob.updates_left > 0,
            db.func.char_length(db.WalletBlob.blob) < len(blob)).update({
                'updates_left': db.WalletBlob.updates_left - 1,
                'blob': blob})
        result = format_blob(record).next()
        return current_app.encode_success(result)


class User(Resource):

    @login_required
    def post(self):
        """Return the blobs stored for this user."""
        only_count = int(g.payload.get('count', 0))

        blobs = current_app.session.query(db.WalletBlob).filter(
            db.WalletBlob.user_id == current_user.id)

        if only_count:
            # Return the number of blobs stored.
            result = {'num': blobs.count()}
        else:
            # Return the actual blobs.
            result = list(format_blob(*blobs))

        return current_app.encode_success(result)


blueprint = Blueprint('user', __name__)

api = Api(blueprint)
api.add_resource(UserSignup, '/user/signup')
api.add_resource(UserData, '/user/data')
api.add_resource(UserStoreBlob, '/user/blob')
api.add_resource(User, '/user')
