async function exec() {
  if (!this._model) {
    throw new Error('Aggregate not bound to any Model');
  }
  if (typeof arguments[0] === 'function') {
    throw new MongooseError('Aggregate.prototype.exec() no longer accepts a callback');
  }
  const model = this._model;
  const collection = this._model.collection;

  applyGlobalMaxTimeMS(this.options, model.db.options, model.base.options);
  applyGlobalDiskUse(this.options, model.db.options, model.base.options);

  const asyncLocalStorage = this.model()?.db?.base.transactionAsyncLocalStorage?.getStore();
  if (!this.options.hasOwnProperty('session') && asyncLocalStorage?.session != null) {
    this.options.session = asyncLocalStorage.session;
  }

  if (this.options && this.options.cursor) {
    return new AggregationCursor(this);
  }

  prepareDiscriminatorPipeline(this._pipeline, this._model.schema);
  stringifyFunctionOperators(this._pipeline);

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

  if (!this._pipeline.length) {
    throw new MongooseError('Aggregate has empty pipeline');
  }

  const options = clone(this.options || {});
  let result;
  try {
    const cursor = await collection.aggregate(this._pipeline, options);
    result = await cursor.toArray();
  } catch (error) {
    await new Promise((resolve, reject) => {
      const _opts = { error: error };
      model.hooks.execPost('aggregate', this, [null], _opts, (error) => {
        if (error) {
          return reject(error);
        }

        resolve();
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