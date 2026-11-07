async function explain(verbosity) {
  if (typeof verbosity === 'function' || typeof arguments[1] === 'function') {
    throw new MongooseError('Aggregate.prototype.explain() no longer accepts a callback');
  }
  const model = this._model;

  if (!this._pipeline.length) {
    throw new Error('Aggregate has empty pipeline');
  }

  prepareDiscriminatorPipeline(this._pipeline, this._model.schema);

  await new Promise((resolve, reject) => {
    model.hooks.execPre('aggregate', this, error => {
      if (error) {
        const _opts = { error: error };
        return model.hooks.execPost('aggregate', this, [null], _opts, error => {
          reject(error);
        });
      } else {
        resolve();
      }
    });
  });

  const cursor = model.collection.aggregate(this._pipeline, this.options);

  if (verbosity == null) {
    verbosity = true;
  }

  let result = null;
  try {
    result = await cursor.explain(verbosity);
  } catch (error) {
    await new Promise((resolve, reject) => {
      const _opts = { error: error };
      model.hooks.execPost('aggregate', this, [null], _opts, error => {
        if (error) {
          return reject(error);
        }
        return resolve();
      });
    });
  }

  const _opts = { error: null };
  await new Promise((resolve, reject) => {
    model.hooks.execPost('aggregate', this, [result], _opts, error => {
      if (error) {
        return reject(error);
      }
      return resolve();
    });
  });

  return result;
}