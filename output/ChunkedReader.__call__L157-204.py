def __call__(self, buf: ReceiveBuffer) -> Union[Data, EndOfMessage, None]:
        if self._reading_trailer:
            lines = buf.maybe_extract_lines()
            if lines is None:
                return None
            return EndOfMessage(headers=list(_decode_header_lines(lines)))
        if self._bytes_to_discard > 0:
            data = buf.maybe_extract_at_most(self._bytes_to_discard)
            if data is None:
                return None
            expected = b"\r\n"[2 - self._bytes_to_discard :]
            if data != expected[: len(data)]:
                raise LocalProtocolError("malformed chunked body: missing CRLF")
            self._bytes_to_discard -= len(data)
            if self._bytes_to_discard > 0:
                return None
            # else, fall through and read some more
        assert self._bytes_to_discard == 0
        if self._bytes_in_chunk == 0:
            # We need to refill our chunk count
            chunk_header = buf.maybe_extract_next_line()
            if chunk_header is None:
                return None
            matches = validate(
                chunk_header_re,
                chunk_header,
                "illegal chunk header: {!r}",
                chunk_header,
            )
            # XX FIXME: we discard chunk extensions. Does anyone care?
            self._bytes_in_chunk = int(matches["chunk_size"], base=16)
            if self._bytes_in_chunk == 0:
                self._reading_trailer = True
                return self(buf)
            chunk_start = True
        else:
            chunk_start = False
        assert self._bytes_in_chunk > 0
        data = buf.maybe_extract_at_most(self._bytes_in_chunk)
        if data is None:
            return None
        self._bytes_in_chunk -= len(data)
        if self._bytes_in_chunk == 0:
            self._bytes_to_discard = 2
            chunk_end = True
        else:
            chunk_end = False
        return Data(data=data, chunk_start=chunk_start, chunk_end=chunk_end)