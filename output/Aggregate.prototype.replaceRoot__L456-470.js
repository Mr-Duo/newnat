function(newRoot) {
  let ret;

  if (typeof newRoot === 'string') {
    ret = newRoot.startsWith('$') ? newRoot : '$' + newRoot;
  } else {
    ret = newRoot;
  }

  return this.append({
    $replaceRoot: {
      newRoot: ret
    }
  });
}