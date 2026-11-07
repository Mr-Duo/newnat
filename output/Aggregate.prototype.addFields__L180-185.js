function(arg) {
  if (typeof arg !== 'object' || arg === null || Array.isArray(arg)) {
    throw new Error('Invalid addFields() argument. Must be an object');
  }
  return this.append({ $addFields: Object.assign({}, arg) });
}