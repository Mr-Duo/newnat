func New(opts ...Opts) (Manifest, error) {
	mc := manifestConfig{}
	for _, opt := range opts {
		opt(&mc)
	}
	c := common{
		r:         mc.r,
		desc:      mc.desc,
		rawBody:   mc.raw,
		expected:  mc.expected,
		rawHeader: mc.header,
	}
	// Keep every integrity constraint separately; none of the untrusted response
	// metadata may replace an expected digest supplied by the caller.
	if mc.desc.Digest != "" {
		c.expected = append(c.expected, mc.desc.Digest)
	}
	if mc.r.Digest != "" {
		refDigest, err := digest.Parse(mc.r.Digest)
		if err != nil {
			return nil, fmt.Errorf("invalid reference digest %q: %w", mc.r.Digest, err)
		}
		c.expected = append(c.expected, refDigest)
		if c.desc.Digest == "" {
			c.desc.Digest = refDigest
		}
	}
	// extract fields from header where available
	if mc.header != nil {
		if c.desc.MediaType == "" {
			c.desc.MediaType = mediatype.Base(mc.header.Get("Content-Type"))
		}
		if c.desc.Size == 0 {
			cl, _ := strconv.Atoi(mc.header.Get("Content-Length"))
			c.desc.Size = int64(cl)
		}
		for _, headerDigestStr := range mc.header.Values("Docker-Content-Digest") {
			if headerDigestStr == "" {
				continue
			}
			headerDigest, err := digest.Parse(headerDigestStr)
			if err != nil {
				return nil, fmt.Errorf("invalid Docker-Content-Digest %q: %w", headerDigestStr, err)
			}
			c.expected = append(c.expected, headerDigest)
			if c.desc.Digest == "" {
				c.desc.Digest = headerDigest
			}
		}
		c.setRateLimit(mc.header)
	}
	if mc.orig != nil {
		return fromOrig(c, mc.orig)
	}
	return fromCommon(c)
}