func WithOrig(orig interface{}) Opts {
	return func(mc *manifestConfig) {
		mc.orig = orig
	}
}