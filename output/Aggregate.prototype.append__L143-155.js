function() {
  const args = (arguments.length === 1 && Array.isArray(arguments[0]))
    ? arguments[0]
    : [...arguments];

  if (!args.every(isOperator)) {
    throw new Error('Arguments must be aggregate pipeline operators');
  }

  this._pipeline = this._pipeline.concat(args);

  return this;
}