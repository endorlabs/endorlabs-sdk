"""Unit tests for call graph protobuf decoding."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from endorlabs.resources import call_graph_data_proto as proto_mod


def test_decode_callgraph_rejects_oversized_decompression() -> None:
    envelope = {"zstd_bytes": "dGVzdA=="}  # base64 "test"
    with (
        patch.object(proto_mod, "_HAS_ZSTD", True),
        patch.object(proto_mod, "zstandard") as mock_zstd,
    ):
        mock_zstd.ZstdError = Exception
        mock_zstd.ZstdDecompressor.return_value.decompress.side_effect = (
            mock_zstd.ZstdError("decompression error: Frame requires too much memory")
        )
        with pytest.raises(ValueError, match="Call graph decompression failed"):
            proto_mod.decode_callgraph(envelope)
