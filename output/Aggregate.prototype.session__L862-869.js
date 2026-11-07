function(session) {
  if (session == null) {
    delete this.options.session;
  } else {
    this.options.session = session;
  }
  return this;
}