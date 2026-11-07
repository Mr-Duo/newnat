function(size) {
  return this.append({ $sample: { size: size } });
}