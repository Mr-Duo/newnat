func verifyDigests(expected []digest.Digest, content []byte) error {
	for _, want := range expected {
		if want == "" {
			continue
		}
		if err := want.Validate(); err != nil {
			return fmt.Errorf("invalid manifest digest %s: %w", want, err)
		}
		got := want.Algorithm().FromBytes(content)
		if want != got {
			return fmt.Errorf("manifest digest mismatch, expected %s, computed %s", want, got)
		}
	}
	return nil
}