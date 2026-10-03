"""Master of Garden's MessagePack protocol, independent of HTTP and storage."""
from .codec import CodecError, decode, encode, decode_document, encode_document

__all__ = ["CodecError", "decode", "encode", "decode_document", "encode_document"]
