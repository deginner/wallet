__all__ = ['MIN_ITERCOUNT', 'MIN_SALTENTROPY', 'MAX_USERNAMELEN',
           'MAX_BLOBLEN', 'MAX_NEWADDRESS']

MAX_USERNAMELEN = 20
MAX_BLOBLEN = 8192      # A blob may not contain more than 8k bytes.
MAX_BLOBCOUNT = 8       # Users are limited to 8 wallets.

MIN_ITERCOUNT = 10000   # Iterations used by the client in PBKDF2.
MIN_SALTENTROPY = 0.95  # Range: [0, 1]

# Maximum number of addresses that may be derived in one request.
MAX_NEWADDRESS = 100
