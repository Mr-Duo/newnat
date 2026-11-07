func OCIIndexToAny(ociI v1.Index, origP interface{}) error {
	// reflect is used to handle both *interface{} and *Manifest
	rv := reflect.ValueOf(origP)
	for rv.IsValid() && rv.Type().Kind() == reflect.Ptr {
		rv = rv.Elem()
	}
	if !rv.IsValid() {
		return fmt.Errorf("invalid manifest output parameter: %T", origP)
	}
	if !rv.CanSet() {
		return fmt.Errorf("manifest output must be a pointer: %T", origP)
	}
	origR := rv.Interface()
	switch orig := (origR).(type) {
	case schema2.ManifestList:
		orig.Versioned = schema2.ManifestListSchemaVersion
		orig.Manifests = ociI.Manifests
		orig.Annotations = ociI.Annotations
		rv.Set(reflect.ValueOf(orig))
	case v1.Index:
		rv.Set(reflect.ValueOf(ociI))
	default:
		return fmt.Errorf("unable to convert OCI index to %T", origR)
	}
	return nil
}