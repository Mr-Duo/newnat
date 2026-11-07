function(name, schema) {
  class Model extends exports.Document {
    constructor(obj, fields) {
      super(obj, schema, fields);
    }
  }
  Model.modelName = name;

  return Model;
}