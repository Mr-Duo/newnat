func GetPlatformList(m Manifest) ([]*platform.Platform, error) {
	mi, ok := m.(Indexer)
	if !ok {
		return nil, fmt.Errorf("unsupported manifest type: %s", m.GetDescriptor().MediaType)
	}
	dl, err := mi.GetManifestList()
	if err != nil {
		return nil, fmt.Errorf("failed to get manifest list: %w", err)
	}
	return getPlatformList(dl)
}