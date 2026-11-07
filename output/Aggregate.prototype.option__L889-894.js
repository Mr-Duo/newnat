function(value) {
  for (const key in value) {
    this.options[key] = value[key];
  }
  return this;
}