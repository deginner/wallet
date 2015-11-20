"""
Handles server-side cosigner creation and utilities related to it.
"""
import logging

from flask import Blueprint, current_app, g
from flask.ext.restful import Api, Resource
from flask.ext.login import login_required, current_user

from .. import database as db
from ..error import Errors, ErrorCode, COSIGNER_ERR
from ..constant import MAX_NEWADDRESS


def insert(record):
    session = current_app.session
    session.add(record)
    try:
        session.commit()
        return current_app.encode_success()
    except Exception:
        logging.exception("Failed to commit cowallet record")
        session.rollback()
        resp = current_app.encode_error(Errors.GenericError)
        return resp
    finally:
        session.close()


class CosignerCreate(Resource):

    @login_required
    def post(self):
        """
        Add a cosigner controlled by this server to a given wallet.

        Parameters required from the client:
            * secret [text]    - secret required to join the wallet
            * id [text]        - wallet ID for this cosigner to join
        """
        join_secret = g.payload.get('secret', '').encode('ascii')
        wallet_id = g.payload.get('id', '').encode('ascii')
        if not wallet_id or not join_secret:
            return current_app.encode_error(Errors.MissingArguments)

        # Check that the wallet belongs to this user.
        count = current_app.session.query(db.WalletBlob).filter(
            db.WalletBlob.user_id == current_user.id,
            db.WalletBlob.id == wallet_id).count()
        if not count:
            return current_app.encode_error(Errors.WalletNotFound)

        # Send the join request to the cosigning server.
        resp = current_app.cosigner(
            '/join', secret=join_secret, walletId=wallet_id)
        if resp is None:
            # Cosigner server is not available.
            return current_app.encode_error(Errors.CosigningDisabled)
        if 'wallet' not in resp:
            logging.info(resp)
            err = ErrorCode(COSIGNER_ERR, resp['error'])
            return current_app.encode_error(err)

        # Store the cosigner wallet.
        cowallet = db.CosignerWallet(
            wallet_id=wallet_id,
            user_id=current_user.id,
            wallet=resp['wallet'])
        result = insert(cowallet)

        return result


class Address(Resource):

    @login_required
    def post(self):
        """
        Create new address(es). This only available when the wallet has
        a server-controlled cosigner.

        Parameters required from the client:
            * id [text]    - wallet ID

        Optional parameters:
            * num [number] - number of addresses to obtain
                             (max: 100, default: 1)
        """
        num = int(g.payload.get('num', 1))
        wallet_id = g.payload.get('id', '').encode('ascii')
        if not wallet_id:
            return current_app.encode_error(Errors.MissingArguments)
        if num <= 0 or num > MAX_NEWADDRESS:
            return current_app.encode_error(Errors.InvalidAddressCount)

        # Get the cosigner for this wallet for this user.
        record = current_app.session.query(db.CosignerWallet).filter(
            db.CosignerWallet.user_id == current_user.id,
            db.CosignerWallet.wallet_id == wallet_id).one_or_none()
        if record is None:
            return current_app.encode_error(Errors.CosignerNotFound)

        # Send the request to the cosigning server.
        resp = current_app.cosigner(
            '/address/new', num=num, wallet=record.wallet)

        if 'address' in resp:
            keys = ['address', 'path', 'createdOn']
            if isinstance(resp['address'], dict):
                # Single address derived.
                keys.append('walletId')
                data = {key: resp['address'][key] for key in keys}
            else:
                # Multiple addresses.
                data = {
                    'walletId': resp['address'][0]['walletId'],
                    'result': None
                }
                data['result'] = [{key: entry[key] for key in keys}
                        for entry in resp['address']]
            result = current_app.encode_success(data)
        else:
            logging.error(resp)
            result = current_app.encode_error(Errors.CosignerError)

        return result


class Balance(Resource):

    @login_required
    def post(self):
        """
        Return the balance for a given wallet. The bitcoin balance
        is only available when the wallet has a server-controlled cosigner.

        Parameters required from the client:
            * id [text]    - wallet ID
        """
        wallet_id = g.payload.get('id', '').encode('ascii')
        if not wallet_id:
            return current_app.encode_error(Errors.MissingArguments)

        # Get the cosigner for this wallet for this user.
        record = current_app.session.query(db.CosignerWallet).filter(
            db.CosignerWallet.user_id == current_user.id,
            db.CosignerWallet.wallet_id == wallet_id).one_or_none()
        if record is None:
            return current_app.encode_error(Errors.CosignerNotFound)

        # Send the request to the cosigning server.
        logging.info('still here')
        resp = current_app.cosigner('/balance', wallet=record.wallet)
        logging.info('result %s', resp)
        if 'balance' in resp:
            data = {'btc': resp['balance']}
            result = current_app.encode_success(data)
        else:
            logging.error(resp)
            result = current_app.encode_error(Errors.CosignerError)

        return result


blueprint = Blueprint('cosigner', __name__)

api = Api(blueprint)
api.add_resource(CosignerCreate, '/cosigner')
api.add_resource(Address, '/address')
api.add_resource(Balance, '/balance')
