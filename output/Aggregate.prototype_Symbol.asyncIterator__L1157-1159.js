function() {
    return this.cursor({ useMongooseAggCursor: true }).transformNull()._transformForAsyncIterator();
  }