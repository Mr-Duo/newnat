func OCIManifestFromAny(orig interface{}) (v1.Manifest, error) {
	ociM := v1.Manifest{
		Versioned: v1.ManifestSchemaVersion,
		MediaType: mediatype.OCI1Manifest,
	}
	switch orig := orig.(type) {
	case schema2.Manifest:
		ociM.Config = orig.Config
		ociM.Layers = orig.Layers
		ociM.Annotations = orig.Annotations
	case v1.Manifest:
		ociM = orig
	default:
		// TODO: consider supporting Docker schema v1 media types
		return ociM, fmt.Errorf("unable to convert %T to OCI image", orig)
	}
	return ociM, nil
}