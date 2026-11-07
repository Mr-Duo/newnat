func GetDigest(m Manifest) digest.Digest {
	d := m.GetDescriptor()
	return d.Digest
}