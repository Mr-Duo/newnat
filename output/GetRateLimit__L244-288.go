func GetRateLimit(m Manifest) types.RateLimit {
	rl := types.RateLimit{}
	header, err := m.RawHeaders()
	if err != nil {
		return rl
	}
	// check for rate limit headers
	rlLimit := header.Get("RateLimit-Limit")
	rlRemain := header.Get("RateLimit-Remaining")
	rlReset := header.Get("RateLimit-Reset")
	if rlLimit != "" {
		lpSplit := strings.Split(rlLimit, ",")
		lSplit := strings.Split(lpSplit[0], ";")
		rlLimitI, err := strconv.Atoi(lSplit[0])
		if err != nil {
			rl.Limit = 0
		} else {
			rl.Limit = rlLimitI
		}
		if len(lSplit) > 1 {
			rl.Policies = lpSplit
		} else if len(lpSplit) > 1 {
			rl.Policies = lpSplit[1:]
		}
	}
	if rlRemain != "" {
		rSplit := strings.Split(rlRemain, ";")
		rlRemainI, err := strconv.Atoi(rSplit[0])
		if err != nil {
			rl.Remain = 0
		} else {
			rl.Remain = rlRemainI
			rl.Set = true
		}
	}
	if rlReset != "" {
		rlResetI, err := strconv.Atoi(rlReset)
		if err != nil {
			rl.Reset = 0
		} else {
			rl.Reset = rlResetI
		}
	}
	return rl
}