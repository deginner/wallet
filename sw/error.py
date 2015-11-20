from collections import namedtuple

from .constant import (MIN_ITERCOUNT, MAX_USERNAMELEN, MAX_BLOBLEN,
                       MAX_NEWADDRESS)

__all__ = ['ErrorCode', 'Errors', 'COSIGNER_ERR']

COSIGNER_ERR = 1004

ErrorCode = namedtuple('ErrorCode', 'code reason')

class Errors:
    UserNotFound = ErrorCode(404, 'user not found')
    WalletNotFound = ErrorCode(404, 'wallet not found')
    CosignerNotFound = ErrorCode(404, 'cosigner not found for this wallet')

    GenericError = ErrorCode(700, 'request could not be processed')
    MissingArguments = ErrorCode(701, 'request is missing arguments')
    InvalidMessage = ErrorCode(702, 'invalid JWS message')

    InvalidSignature = ErrorCode(900, 'signature does not match')
    InvalidNonce = ErrorCode(901,
        'nonce must be positive and greater than the last one')
    InvalidUsername = ErrorCode(902, 'username already in use')
    InvalidAddressCount = ErrorCode(903,
        'num must be between 1 and {}'.format(MAX_NEWADDRESS))

    UsernameTooLong = ErrorCode(1000,
        'username is too long, keep it below {} chars'.format(MAX_USERNAMELEN))
    LowIterCount = ErrorCode(1001,
        'iteration count must be at least {}'.format(MIN_ITERCOUNT))
    BadSalt = ErrorCode(1002, 'salt is not random enough')
    BlobTooLong = ErrorCode(1003,
        'blob is too long, keep it below {} chars'.format(MAX_BLOBLEN))

    TooManyBlobs = ErrorCode(1429, 'no more blobs allowed for this account')
    CosigningDisabled = ErrorCode(1404, 'cosigning not available')
    CosignerError = ErrorCode(1500, 'cosigner could not complete request')
