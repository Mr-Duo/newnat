func verifyMT(expected, received string) error {
	if received != "" && expected != received {
		return fmt.Errorf("manifest contains an unexpected media type: expected %s, received %s", expected, received)
	}
	return nil
}