function Aggregate(pipeline, model) {
  this._pipeline = [];
  this._model = model;
  this.options = {};

  if (arguments.length === 1 && Array.isArray(pipeline)) {
    this.append.apply(this, pipeline);
  }
}