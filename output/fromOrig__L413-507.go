func fromOrig(c common, orig interface{}) (Manifest, error) {
	var mt string
	var m Manifest
	origDigest := c.desc.Digest

	mj, err := json.Marshal(orig)
	if err != nil {
		return nil, err
	}
	c.manifSet = true
	if len(c.rawBody) == 0 {
		c.rawBody = mj
	}
	if _, ok := orig.(schema1.SignedManifest); !ok {
		c.desc.Digest = c.desc.DigestAlgo().FromBytes(mj)
	}
	if c.desc.Size == 0 {
		c.desc.Size = int64(len(mj))
	}
	// create manifest based on type
	switch mOrig := orig.(type) {
	case schema1.Manifest:
		mt = mOrig.MediaType
		c.desc.MediaType = mediatype.Docker1Manifest
		m = &docker1Manifest{
			common:   c,
			Manifest: mOrig,
		}
	case schema1.SignedManifest:
		mt = mOrig.MediaType
		c.desc.MediaType = mediatype.Docker1ManifestSigned
		// recompute digest on the canonical data
		c.desc.Digest = c.desc.DigestAlgo().FromBytes(mOrig.Canonical)
		m = &docker1SignedManifest{
			common:         c,
			SignedManifest: mOrig,
		}
	case schema2.Manifest:
		mt = mOrig.MediaType
		c.desc.MediaType = mediatype.Docker2Manifest
		m = &docker2Manifest{
			common:   c,
			Manifest: mOrig,
		}
	case schema2.ManifestList:
		mt = mOrig.MediaType
		c.desc.MediaType = mediatype.Docker2ManifestList
		m = &docker2ManifestList{
			common:       c,
			ManifestList: mOrig,
		}
	case v1.Manifest:
		mt = mOrig.MediaType
		c.desc.MediaType = mediatype.OCI1Manifest
		m = &oci1Manifest{
			common:   c,
			Manifest: mOrig,
		}
	case v1.Index:
		mt = mOrig.MediaType
		c.desc.MediaType = mediatype.OCI1ManifestList
		m = &oci1Index{
			common: c,
			Index:  orig.(v1.Index),
		}
	case v1.ArtifactManifest:
		mt = mOrig.MediaType
		c.desc.MediaType = mediatype.OCI1Artifact
		m = &oci1Artifact{
			common:           c,
			ArtifactManifest: mOrig,
		}
	default:
		return nil, fmt.Errorf("unsupported type to convert to a manifest: %T", orig)
	}
	// verify media type
	err = verifyMT(c.desc.MediaType, mt)
	if err != nil {
		return nil, err
	}
	// Verify caller constraints against canonical bytes for schema1 signatures.
	verifyContent := mj
	if signed, ok := orig.(schema1.SignedManifest); ok {
		verifyContent = signed.Canonical
	}
	if len(verifyContent) > 0 {
		if err := verifyDigests(c.expected, verifyContent); err != nil {
			return nil, err
		}
	}
	if origDigest != "" && len(c.expected) == 0 && origDigest != c.desc.Digest {
		return nil, fmt.Errorf("manifest digest mismatch, expected %s, computed %s", origDigest, c.desc.Digest)
	}
	return m, nil
}