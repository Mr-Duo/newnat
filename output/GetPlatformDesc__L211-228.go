func GetPlatformDesc(m Manifest, p *platform.Platform) (*descriptor.Descriptor, error) {
	if p == nil {
		return nil, fmt.Errorf("invalid input, platform is nil%.0w", errs.ErrNotFound)
	}
	mi, ok := m.(Indexer)
	if !ok {
		return nil, fmt.Errorf("unsupported manifest type: %s", m.GetDescriptor().MediaType)
	}
	dl, err := mi.GetManifestList()
	if err != nil {
		return nil, fmt.Errorf("failed to get manifest list: %w", err)
	}
	d, err := descriptor.DescriptorListSearch(dl, descriptor.MatchOpt{Platform: p})
	if err != nil {
		return nil, fmt.Errorf("platform not found: %s%.0w", *p, err)
	}
	return &d, nil
}