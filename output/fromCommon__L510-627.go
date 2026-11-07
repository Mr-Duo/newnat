func fromCommon(c common) (Manifest, error) {
	var err error
	var m Manifest
	var mt string
	var verifyContent []byte
	// extract common data from from rawBody
	if len(c.rawBody) > 0 {
		c.manifSet = true
		// extract media type from body, either explicitly or with duck typing
		if c.desc.MediaType == "" {
			mt := struct {
				MediaType     string                  `json:"mediaType,omitempty"`
				SchemaVersion int                     `json:"schemaVersion,omitempty"`
				Signatures    []interface{}           `json:"signatures,omitempty"`
				Manifests     []descriptor.Descriptor `json:"manifests,omitempty"`
				Layers        []descriptor.Descriptor `json:"layers,omitempty"`
			}{}
			err = json.Unmarshal(c.rawBody, &mt)
			if mt.MediaType != "" {
				c.desc.MediaType = mt.MediaType
			} else if mt.SchemaVersion == 1 && len(mt.Signatures) > 0 {
				c.desc.MediaType = mediatype.Docker1ManifestSigned
			} else if mt.SchemaVersion == 1 {
				c.desc.MediaType = mediatype.Docker1Manifest
			} else if len(mt.Manifests) > 0 {
				if strings.HasPrefix(mt.Manifests[0].MediaType, "application/vnd.docker.") {
					c.desc.MediaType = mediatype.Docker2ManifestList
				} else {
					c.desc.MediaType = mediatype.OCI1ManifestList
				}
			} else if len(mt.Layers) > 0 {
				if strings.HasPrefix(mt.Layers[0].MediaType, "application/vnd.docker.") {
					c.desc.MediaType = mediatype.Docker2Manifest
				} else {
					c.desc.MediaType = mediatype.OCI1Manifest
				}
			}
		}
		// compute digest
		if c.desc.MediaType != mediatype.Docker1ManifestSigned {
			verifyContent = c.rawBody
			d := c.desc.DigestAlgo().FromBytes(c.rawBody)
			c.desc.Digest = d
			c.desc.Size = int64(len(c.rawBody))
		}
	}
	switch c.desc.MediaType {
	case mediatype.Docker1Manifest:
		var mOrig schema1.Manifest
		if len(c.rawBody) > 0 {
			err = json.Unmarshal(c.rawBody, &mOrig)
			mt = mOrig.MediaType
		}
		m = &docker1Manifest{common: c, Manifest: mOrig}
	case mediatype.Docker1ManifestSigned:
		var mOrig schema1.SignedManifest
		if len(c.rawBody) > 0 {
			err = json.Unmarshal(c.rawBody, &mOrig)
			mt = mOrig.MediaType
			verifyContent = mOrig.Canonical
			d := c.desc.DigestAlgo().FromBytes(mOrig.Canonical)
			c.desc.Digest = d
			c.desc.Size = int64(len(mOrig.Canonical))
		}
		m = &docker1SignedManifest{common: c, SignedManifest: mOrig}
	case mediatype.Docker2Manifest:
		var mOrig schema2.Manifest
		if len(c.rawBody) > 0 {
			err = json.Unmarshal(c.rawBody, &mOrig)
			mt = mOrig.MediaType
		}
		m = &docker2Manifest{common: c, Manifest: mOrig}
	case mediatype.Docker2ManifestList:
		var mOrig schema2.ManifestList
		if len(c.rawBody) > 0 {
			err = json.Unmarshal(c.rawBody, &mOrig)
			mt = mOrig.MediaType
		}
		m = &docker2ManifestList{common: c, ManifestList: mOrig}
	case mediatype.OCI1Manifest:
		var mOrig v1.Manifest
		if len(c.rawBody) > 0 {
			err = json.Unmarshal(c.rawBody, &mOrig)
			mt = mOrig.MediaType
		}
		m = &oci1Manifest{common: c, Manifest: mOrig}
	case mediatype.OCI1ManifestList:
		var mOrig v1.Index
		if len(c.rawBody) > 0 {
			err = json.Unmarshal(c.rawBody, &mOrig)
			mt = mOrig.MediaType
		}
		m = &oci1Index{common: c, Index: mOrig}
	case mediatype.OCI1Artifact:
		var mOrig v1.ArtifactManifest
		if len(c.rawBody) > 0 {
			err = json.Unmarshal(c.rawBody, &mOrig)
			mt = mOrig.MediaType
		}
		m = &oci1Artifact{common: c, ArtifactManifest: mOrig}
	default:
		return nil, fmt.Errorf("%w: \"%s\"", errs.ErrUnsupportedMediaType, c.desc.MediaType)
	}
	if err != nil {
		return nil, fmt.Errorf("error unmarshaling manifest for %s: %w", c.r.CommonName(), err)
	}
	// verify media type
	err = verifyMT(c.desc.MediaType, mt)
	if err != nil {
		return nil, err
	}
	if len(verifyContent) > 0 {
		if err := verifyDigests(c.expected, verifyContent); err != nil {
			return nil, err
		}
	}
	return m, nil
}