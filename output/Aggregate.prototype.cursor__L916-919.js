function(options) {
  this.options.cursor = options || {};
  return new AggregationCursor(this); // return this;
}