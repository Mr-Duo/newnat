func WithDesc(desc descriptor.Descriptor) Opts {
	return func(mc *manifestConfig) {
		mc.desc = desc
	}
}