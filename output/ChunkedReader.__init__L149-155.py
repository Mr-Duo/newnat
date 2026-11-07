def __init__(self) -> None:
        self._bytes_in_chunk = 0
        # After reading a chunk, we have to throw away the trailing \r\n; if
        # this is >0 then we discard that many bytes before resuming regular
        # de-chunkification.
        self._bytes_to_discard = 0
        self._reading_trailer = False