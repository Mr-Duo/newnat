func getPlatformList(dl []descriptor.Descriptor) ([]*platform.Platform, error) {
	var l []*platform.Platform
	for _, d := range dl {
		if d.Platform != nil {
			l = append(l, d.Platform)
		}
	}
	return l, nil
}