func WithHeader(header http.Header) Opts {
	return func(mc *manifestConfig) {
		mc.header = header
	}
}