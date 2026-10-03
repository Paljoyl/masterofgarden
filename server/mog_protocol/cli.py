"""Local file tools. No HTTP requests, login actions, or traffic modification."""
import argparse
import json
from pathlib import Path
import sys

from .capture import CaptureError, iter_api_messages
from .codec import (CodecError, DOCUMENT_FORMAT, MAX_BODY_BYTES, decode, decode_document,
                    encode, encode_document, from_jsonable, to_jsonable)
from .schema import DEFAULT_SCHEMAS, SchemaRegistry, extract_schemas


def _reject_constant(_):
    raise CodecError("Non-finite JSON numbers must use a $msgpack tag")


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"), parse_constant=_reject_constant)


def _write_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + "\n", encoding="utf-8")


def _read_body(path):
    with Path(path).open("rb") as source:
        body = source.read(MAX_BODY_BYTES + 1)
    if len(body) > MAX_BODY_BYTES:
        raise CodecError("Input body exceeds the size limit")
    return body


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Master of Garden MessagePack encoder/decoder")
    sub = parser.add_subparsers(dest="command", required=True)
    dec = sub.add_parser("decode", help="Decode a raw HTTP MessagePack body to JSON")
    dec.add_argument("input", type=Path)
    dec.add_argument("-o", "--output", type=Path, required=True)
    dec.add_argument("--document", action="store_true", help="Preserve original bytes for an exact round trip")
    dec.add_argument("--type", help="Render indexed arrays using a C# model name")
    dec.add_argument("--schemas", type=Path, default=DEFAULT_SCHEMAS)
    enc = sub.add_parser("encode", help="Encode JSON or a decoded document to a binary body")
    enc.add_argument("input", type=Path)
    enc.add_argument("-o", "--output", type=Path, required=True)
    enc.add_argument("--single-float", action="store_true", help="Use float32 when re-encoding edited/new values")
    enc.add_argument("--schemas", type=Path, default=DEFAULT_SCHEMAS)
    cap = sub.add_parser("capture", help="Export all MessagePack messages from a saved .mitm file")
    cap.add_argument("input", type=Path)
    cap.add_argument("-o", "--output", type=Path, required=True)
    cap.add_argument("--schemas", type=Path, default=DEFAULT_SCHEMAS)
    cap.add_argument("--no-names", action="store_true", help="Only export positional values")
    gen = sub.add_parser("import-dump", help="Generate indexed schemas and endpoint mappings from dump.cs")
    gen.add_argument("input", type=Path)
    gen.add_argument("-o", "--output", type=Path, default=DEFAULT_SCHEMAS)
    args = parser.parse_args(argv)
    try:
        if args.input.resolve() == args.output.resolve():
            raise CodecError("Input and output must be different files")
        if args.command == "decode":
            body = _read_body(args.input)
            if args.type:
                registry = SchemaRegistry(args.schemas)
                if args.type not in registry.models:
                    raise CodecError("Unknown schema model: " + args.type)
                result = {"format": "mog-named-msgpack-v1", "type": args.type,
                          "value": registry.named(decode(body), args.type), "original_hex": body.hex()}
            else:
                result = decode_document(body) if args.document else to_jsonable(decode(body))
            _write_json(args.output, result)
            print(f"Decoded {len(body)} bytes -> {args.output}")
        elif args.command == "encode":
            document = _read_json(args.input)
            if isinstance(document, dict) and document.get("format") == DOCUMENT_FORMAT:
                body = encode_document(document, single_float=args.single_float)
            elif isinstance(document, dict) and document.get("format") == "mog-named-msgpack-v1":
                registry = SchemaRegistry(args.schemas)
                model = document.get("type")
                if not isinstance(model, str) or model not in registry.models:
                    raise CodecError("Unknown named document schema")
                value = registry.positional(document["value"], model)
                positional = {"format": DOCUMENT_FORMAT, "value": to_jsonable(value)}
                if "original_hex" in document:
                    positional["original_hex"] = document["original_hex"]
                body = encode_document(positional, single_float=args.single_float)
            else:
                body = encode(from_jsonable(document), single_float=args.single_float)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(body)
            print(f"Encoded {len(body)} bytes -> {args.output}")
        elif args.command == "import-dump":
            schemas = extract_schemas(args.input)
            _write_json(args.output, schemas)
            print(f"Imported {len(schemas['models'])} models and {len(schemas['endpoints'])} endpoints -> {args.output}")
        elif args.command == "capture":
            registry = None if args.no_names else SchemaRegistry(args.schemas)
            records = []
            exact = semantic = 0
            for message in iter_api_messages(args.input):
                document = decode_document(message.body)
                value = decode(message.body)
                if encode_document(document) != message.body:
                    raise CodecError("Exact round trip failed at flow " + str(message.flow_index))
                exact += 1
                repacked = encode(from_jsonable(document["value"]))
                if to_jsonable(decode(repacked)) != document["value"]:
                    raise CodecError("Semantic round trip failed at flow " + str(message.flow_index))
                semantic += 1
                record = {"flow_index": message.flow_index, "host": message.host,
                          "method": message.method, "path": message.path,
                          "direction": message.direction, "status": message.status,
                          "body_bytes": len(message.body), "body": document}
                endpoint = registry.endpoint(message.method, message.path) if registry else None
                if endpoint:
                    model = endpoint.get(message.direction)
                    if model:
                        record["model"] = model
                        record["named"] = registry.named(value, model)
                records.append(record)
            result = {"format": "mog-capture-v1", "source": args.input.name,
                      "messages": records, "validation": {
                          "byte_exact_documents": exact, "semantic_reencodes": semantic}}
            _write_json(args.output, result)
            print(f"Exported {len(records)} messages; exact={exact}, semantic={semantic} -> {args.output}")
        return 0
    except (CodecError, CaptureError, OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        # Library error text may include account payloads; expose only our own errors.
        detail = str(exc) if isinstance(exc, (CodecError, CaptureError)) else type(exc).__name__
        print("Error: " + detail, file=sys.stderr)
        return 1
