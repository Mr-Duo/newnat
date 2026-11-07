func OCIIndexFromAny(orig interface{}) (v1.Index, error) {
	ociI := v1.Index{
		Versioned: v1.IndexSchemaVersion,
		MediaType: mediatype.OCI1ManifestList,
	}
	switch orig := orig.(type) {
	case schema2.ManifestList:
		ociI.Manifests = orig.Manifests
		ociI.Annotations = orig.Annotations
	case v1.Index:
		ociI = orig
	default:
		return ociI, fmt.Errorf("unable to convert %T to OCI index", orig)
	}
	return ociI, nil
}