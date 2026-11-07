function(arg) {
  // TODO refactor to reuse the query builder logic

  const sort = {};

  if (getConstructorName(arg) === 'Object') {
    const desc = ['desc', 'descending', -1];
    Object.keys(arg).forEach(function(field) {
      // If sorting by text score, skip coercing into 1/-1
      if (arg[field] instanceof Object && arg[field].$meta) {
        sort[field] = arg[field];
        return;
      }
      sort[field] = desc.indexOf(arg[field]) === -1 ? 1 : -1;
    });
  } else if (arguments.length === 1 && typeof arg === 'string') {
    arg.split(/\s+/).forEach(function(field) {
      if (!field) {
        return;
      }
      const ascend = field[0] === '-' ? -1 : 1;
      if (ascend === -1) {
        field = field.substring(1);
      }
      sort[field] = ascend;
    });
  } else {
    throw new TypeError('Invalid sort() argument. Must be a string or object.');
  }

  return this.append({ $sort: sort });
}