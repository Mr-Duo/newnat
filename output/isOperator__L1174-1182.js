function isOperator(obj) {
  if (typeof obj !== 'object' || obj === null) {
    return false;
  }

  const k = Object.keys(obj);

  return k.length === 1 && k[0][0] === '$';
}