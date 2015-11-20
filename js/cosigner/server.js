"use strict";

var url = require('url');
var config = require('config');
var logger = require('morgan');
var express = require('express');
var bodyParser = require('body-parser');
var MongoClient = require('mongodb').MongoClient;
var cosigner = require('./cosigner');
var error = require('./error');

var parsed = url.parse(config.get('cosigner_server'));
var port = parseInt(parsed.port);
var hostname = parsed.hostname;
var app = express();


/**
 * Check how many cosigners can still join a wallet.
 *
 * @param {object} db       - Returned from a successful MongoClient connection.
 * @param {string} walletId
 * @param {function} cb     - Callback function
 * @returns {number}        - spots left (>= 0)
 */
function spotsLeft(db, walletId, cb) {
  var col = db.collection('wallets');
  col.findOne({id: walletId}, function(err, res) {
    if (err) {
      return cb(err, false);
    }
    if (!res) {
      return cb('wallet not found', false);
    }

    var total = res.n;
    var left = total - res.copayers.length;
    cb(null, left);
  });
}


/**
 * Setup all the routes and the cosigner server.
 *
 * @param {object} db - Returned from a successful MongoClient connection.
 */
function setup(db) {

  app.use(logger('combined'));
  app.use(bodyParser.json());

  /**
   * Join a multisig wallet.
   *
   * POST params:
   * @param {string} secret
   * @param {string} walletId
   */
  app.post('/join', function(req, res) {
    var secret = req.body.secret;
    var walletId = req.body.walletId;
    if (!secret || !walletId) {
      return res.json(error.fail('missing params'));
    }

    spotsLeft(db, walletId, function(err, left) {
      /* This cosigner rejects to join a wallet unless it's the only
       * remaining to join and complete it. This is done so the wallet
       * that is saved does not need to be updated.
       */
      if (err || left !== 1) {
        if (err) {
          console.error(err);
          return res.json(error.fail(err));
        } else if (left < 1) {
          return res.json(error.fail('wallet is full'));
        } else {
          return res.json(error.fail('other cosigners need to join first'));
        }
      }

      cosigner.join(walletId, secret, function(result) {
        console.log('result', result);
        return res.json(result);
      });
    });
  });

  /**
   * Sign and broadcast a transaction.
   *
   * POST params:
   * @param {string} wallet
   * @param {string} txid
   */
  app.post('/sign', function(req, res) {
    var wallet = req.body.wallet;
    var txid = req.body.txid;
    if (!wallet || !txid) {
      return res.json(error.fail('missing params'));
    }

    cosigner.signAndBroadcast(wallet, txid, function(result) {
      console.log('result', result);
      return res.json(result);
    });
  });

  /**
   * Derive a new address for the multisig wallet.
   *
   * POST params:
   * @param {string} wallet
   *
   * Optional POST params:
   * @param {number} num    - number of addresses to derive
   */
  app.post('/address/new', function(req, res) {
    var wallet = req.body.wallet;
    var num = parseInt(req.body.num) || 1;
    if (!wallet) {
      return res.json(error.fail('missing params'));
    }
    if (isNaN(num) || num < 1) {
      return res.json(error.fail('num must be a number greater than 0'));
    }

    cosigner.newAddress(wallet, num, function(result) {
      return res.json(result);
    });
  });

  /**
   * Return the balance for a wallet.
   *
   * POST params:
   * @param {string} wallet
   */
  app.post('/balance', function(req, res) {
    var wallet = req.body.wallet;
    if (!wallet) {
      return res.json(error.fail('missing params'));
    }

    cosigner.balance(wallet, function(result) {
      return res.json(result);
    });
  });

  app.listen(port, hostname, function() {
    console.log('Listening on http://' + hostname + ':' + port);
  });

}


MongoClient.connect(config.get('bws_db'), function(err, db) {
  if (err) {
    throw err;
    return;
  }

  setup(db);
});
