function(arg) {
  const op = {};
  op.$geoNear = arg;
  return this.append(op);
}