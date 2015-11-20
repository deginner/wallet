function fail(msg) {
  var result = msg ? {error: msg} : null;
  return result;
}


module.exports = {
  fail: fail
};
