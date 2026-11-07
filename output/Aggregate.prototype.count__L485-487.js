function(fieldName) {
  return this.append({ $count: fieldName });
}