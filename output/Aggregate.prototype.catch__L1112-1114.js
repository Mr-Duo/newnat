function(reject) {
  return this.exec().then(null, reject);
}