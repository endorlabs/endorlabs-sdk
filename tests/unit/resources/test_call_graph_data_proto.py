"""Unit tests for call graph protobuf decoding."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import zstandard

from endorlabs.resources import call_graph_data_proto as proto_mod


def test_decode_callgraph_rejects_oversized_decompression() -> None:
    envelope = {"zstd_bytes": "dGVzdA=="}  # base64 "test"
    with (
        patch.object(proto_mod, "_HAS_ZSTD", True),
        patch.object(proto_mod, "zstandard") as mock_zstd,
    ):
        mock_zstd.ZstdError = Exception
        mock_zstd.get_frame_parameters.side_effect = mock_zstd.ZstdError("no frame")
        reader = MagicMock()
        reader.read.side_effect = mock_zstd.ZstdError(
            "decompression error: Frame requires too much memory"
        )
        reader.__enter__.return_value = reader
        reader.__exit__.return_value = False
        mock_zstd.ZstdDecompressor.return_value.stream_reader.return_value = reader
        with pytest.raises(ValueError, match="Call graph decompression failed"):
            proto_mod.decode_callgraph(envelope)


def test_decompress_enforces_total_byte_cap() -> None:
    payload = b"x" * 64
    compressed = zstandard.ZstdCompressor().compress(payload)
    out = proto_mod._decompress_callgraph_bytes(compressed, max_bytes=64)
    assert out == payload
    with pytest.raises(ValueError, match="exceeded 16 bytes"):
        proto_mod._decompress_callgraph_bytes(compressed, max_bytes=16)
