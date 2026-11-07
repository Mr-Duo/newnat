func GetMediaType(m Manifest) string {
	d := m.GetDescriptor()
	return d.MediaType
}