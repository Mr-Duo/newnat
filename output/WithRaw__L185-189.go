func WithRaw(raw []byte) Opts {
	return func(mc *manifestConfig) {
		mc.raw = raw
	}
}