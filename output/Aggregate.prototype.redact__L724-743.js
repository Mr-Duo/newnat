function(expression, thenExpr, elseExpr) {
  if (arguments.length === 3) {
    if ((typeof thenExpr === 'string' && !validRedactStringValues.has(thenExpr)) ||
      (typeof elseExpr === 'string' && !validRedactStringValues.has(elseExpr))) {
      throw new Error('If thenExpr or elseExpr is string, it must be either $$DESCEND, $$PRUNE or $$KEEP');
    }

    expression = {
      $cond: {
        if: expression,
        then: thenExpr,
        else: elseExpr
      }
    };
  } else if (arguments.length !== 1) {
    throw new TypeError('Invalid arguments');
  }

  return this.append({ $redact: expression });
}