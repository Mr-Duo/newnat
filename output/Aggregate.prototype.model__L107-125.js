function(model) {
  if (arguments.length === 0) {
    return this._model;
  }

  this._model = model;
  if (model.schema != null) {
    if (this.options.readPreference == null &&
      model.schema.options.read != null) {
      this.options.readPreference = model.schema.options.read;
    }
    if (this.options.collation == null &&
      model.schema.options.collation != null) {
      this.options.collation = model.schema.options.collation;
    }
  }

  return model;
}