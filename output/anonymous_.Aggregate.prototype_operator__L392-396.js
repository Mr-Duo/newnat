function(arg) {
    const op = {};
    op['$' + $operator] = arg;
    return this.append(op);
  }