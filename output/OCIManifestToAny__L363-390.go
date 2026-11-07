func OCIManifestToAny(ociM v1.Manifest, origP interface{}) error {
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
	case schema2.Manifest:
		orig.Versioned = schema2.ManifestSchemaVersion
		orig.Config = ociM.Config
		orig.Layers = ociM.Layers
		orig.Annotations = ociM.Annotations
		rv.Set(reflect.ValueOf(orig))
	case v1.Manifest:
		rv.Set(reflect.ValueOf(ociM))
	default:
		// Docker schema v1 will not be supported, can't resign, and no need for unsigned
		return fmt.Errorf("unable to convert OCI image to %T", origR)
	}
	return nil
}