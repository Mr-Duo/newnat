func HasRateLimit(m Manifest) bool {
	rl := GetRateLimit(m)
	return rl.Set
}