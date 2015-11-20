"use strict";

var config = require('config');
var async = require('async');
var BWC = require('bitcore-wallet-client');
var error = require('./error');
var BWS_URL = config.get('bws_url');

var copayerName = 'this-side-cosigner';


/**
 * Join a multisig wallet.
 *
 * @param {string} walletId
 * @param {string} secret   - secret required to join the wallet
 */
function join(walletId, secret, callback) {

  var client = new BWC({
    verbose: false,
    baseUrl: BWS_URL
  });

  if (BWC.parseSecret(secret).walletId !== walletId) {
    callback(error.fail('walletId does not match'));
    return;
  }

  client.joinWallet(secret, copayerName, null, function(err, wallet) {
    if (err) {
      callback(error.fail(err.toString()));
      return;
    }

    console.log('Joined ' + wallet.name);
    client.openWallet(function(openErr, info) {
      if (openErr) {
        callback(error.fail(openErr));
        return;
      }

      if (info.wallet.status === 'complete') {
        // All good.
        callback({wallet: client.export()});
      } else {
        callback(error.fail('joined, but wallet is not complete'));
      }
    });

  });
}


/**
 * Get a client based on the wallet specified.
 *
 * @param {string} credentials - wallet exported
 * @returns {object}           - a BWC instance
 */
function loadWallet(credentials) {
  var client = new BWC({
    verbose: false,
    baseUrl: BWS_URL
  });

  client.import(credentials);
  if (!client.credentials.isComplete()) {
    throw new Error("wallet is not complete, need more signers");
  }

  return client;
}


/**
 * Return the wallet balance.
 *
 * @param {string} credentials
 */
function balance(credentials, callback) {
  try {
    var client = loadWallet(credentials);
  } catch (err) {
    callback(error.fail(err));
    return;
  }

  client.getBalance(function(err, res) {
    if (err) {
      callback(error.fail(err));
      return;
    }
    callback({balance: res});
  });
}


/**
 * Derive a new address for the multisig wallet.
 *
 * @param {string} credentials
 * @param {number} num         - number of addresses to derive
 */
function newAddress(credentials, num, callback) {
  try {
    var client = loadWallet(credentials);
  } catch (err) {
    callback(error.fail(err));
    return;
  }

  if (num > 100) {
    callback(error.fail('num cannot be greater than 100'));
    return;
  }

  if (num === 1) {
    return oneNewAddress(client, callback);
  }

  var opts = {ignoreMaxGap: true};
  var tasks = Array(num);
  for (var i = 0; i < num; i++) {
    tasks[i] = async.apply(client.createAddress.bind(client), opts);
  }
  async.parallel(tasks, function(err, results) {
    if (err) {
      callback(error.fail(err));
      return;
    }
    callback({address: results});
  });
}


function oneNewAddress(client, callback) {
  var opts = {ignoreMaxGap: true};

  client.createAddress(opts, function(err, address) {
    if (err) {
      callback(error.fail(err));
      return;
    }
    callback({address: address});
  });
}



/**
 * Load wallet from credentials, sign a transaction and then broadcast
 * it if it has enough signatures.
 *
 * @param {string} credentials
 * @param {string} txid
 */
function signAndBroadcast(credentials, txid, callback) {
  try {
    var client = loadWallet(credentials);
  } catch (err) {
    callback(error.fail(err));
    return;
  }

  client.getTx(txid, function(err, tx) {

    if (err) {
      callback(error.fail(err));
      return;
    }

    // Signatures required: m;
    var m = client.credentials.m;

    if (tx.actions.length === m) {
      /* Got into a situation where enough signatures are
       * already present, so just broadcast it. */
      broadcast(client, tx, callback);
      return;
    }

    // Sign only if it's missing one signature.
    if (tx.actions.length !== m - 1) {
      callback(error.fail('need more signatures'));
      return;
    }

    client.signTxProposal(tx, function(signErr, txsigned) {
      if (signErr) {
        callback(error.fail(signErr));
        return;
      }
      // Transaction signed, broadcast it now.
      broadcast(client, txsigned, callback);
    });

  });
}


function broadcast(client, signedtx, callback) {
  client.broadcastTxProposal(signedtx, function(bcastErr, res) {
    if (bcastErr) {
      callback(error.fail(bcastErr));
      return;
    }
    console.log('broadcast', res.txid);
    callback({ok: true});
  });
}


module.exports = {
  join: join,
  loadWallet: loadWallet,
  broadcast: broadcast,
  balance: balance,
  newAddress: newAddress,
  signAndBroadcast: signAndBroadcast
};
