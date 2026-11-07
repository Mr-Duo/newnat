function(arg) {
  if (arg && typeof arg === 'object') {
    return this.append({ $sortByCount: arg });
  } else if (typeof arg === 'string') {
    return this.append({
      $sortByCount: (arg[0] === '$') ? arg : '$' + arg
    });
  } else {
    throw new TypeError('Invalid arg "' + arg + '" to sortByCount(), ' +
      'must be string or object');
  }
}