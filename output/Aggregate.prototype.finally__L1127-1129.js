function(onFinally) {
  return this.exec().finally(onFinally);
}