func WithRef(r ref.Ref) Opts {
	return func(mc *manifestConfig) {
		mc.r = r
	}
}