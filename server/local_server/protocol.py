"""Wire model access for handlers; business services receive validated Python values."""
from copy import deepcopy
from datetime import datetime, timezone

from mog_protocol.codec import CodecError, EMPTY, decode, encode
from mog_protocol.capture import message_body
from .transport import Response


class LocalError(Exception):
    def __init__(self, code, status=400, *, client_message=None):
        self.code = code
        self.status = status
        self.client_message = client_message
        super().__init__(code)


def integer(value, *, minimum=0, maximum=2**63 - 1):
    if type(value) is not int or not minimum <= value <= maximum:
        raise LocalError("invalid_integer")
    return value


def text(value, *, maximum=100, empty=False):
    if not isinstance(value, str) or "\x00" in value or len(value) > maximum or (not empty and not value.strip()):
        raise LocalError("invalid_text")
    return value


def sequence(value, *, maximum=1000):
    if not isinstance(value, list) or len(value) > maximum:
        raise LocalError("invalid_collection")
    return value


class Protocol:
    def __init__(self, registry):
        self.registry = registry
        # Public fields verified in the local dump.cs, absent in the old extractor.
        self.public_fields = {"SetTutorialProgressRequest": {"TutorialProgressInfo": 0},
                              "TutorialProgressInfo": {"Progress": 0},
                              "VerifyPaymentProductRequest": {"ShopPaymentCodes": 0},
                              "CountWithResetTime": {"Count": 1, "LastResetAt": 2}}
        # Non-generic UniTask endpoint omitted by the original schema extractor.
        self.registry.data['endpoints']['POST /shop/verifypaymentproduct'] = {
            'request': 'VerifyPaymentProductRequest', 'response': None,
            'interface': 'IShopApi', 'method': 'PostVerifypaymentproductAsync'}
        self.registry.data['endpoints']['POST /lottery/setlotterycharacterselect'] = {
            'request': 'LotteryCharacterSelectRequest', 'response': None,
            'interface': 'ILotteryApi', 'method': 'PostSetlotterycharacterselectAsync'}

    def indices(self, model):
        return self.public_fields.get(model) or {
            f["name"]: f["index"] for f in self.registry.models[model]["fields"]}

    def fields(self, model, value, *, strict=False):
        indices = self.indices(model)
        length = max(indices.values(), default=-1) + 1
        if value == EMPTY and not indices:
            value = []
        if not isinstance(value, list) or len(value) < length or (strict and len(value) != length):
            raise LocalError("invalid_request_model")
        return {name: value[index] for name, index in indices.items()}

    def request(self, request):
        endpoint = self.registry.endpoint(request.method, request.path)
        if not endpoint or not endpoint["request"]:
            return {}
        payload = message_body({"content": request.body, "headers": list(request.headers.items())})
        return self.fields(endpoint["request"], decode(payload), strict=True)

    def empty_request(self, request):
        payload = message_body({"content": request.body, "headers": list(request.headers.items())})
        if decode(payload) not in (EMPTY, []):
            raise LocalError("invalid_request_model")

    def model(self, model, fields, template=None):
        indices = self.indices(model)
        if set(fields) - indices.keys():
            raise CodecError("Unknown response field")
        value = deepcopy(template) if template is not None else [None] * (max(indices.values(), default=-1) + 1)
        if not isinstance(value, list) or any(indices[name] >= len(value) for name in fields):
            raise CodecError("Incomplete response template")
        for name, item in fields.items():
            value[indices[name]] = deepcopy(item)
        return value

    def response(self, request, fields=None, *, value=None):
        endpoint = self.registry.endpoint(request.method, request.path)
        if value is None:
            value = self.model(endpoint["response"], fields or {})
        return Response(200, [("Content-Type", "application/x-msgpack"),
                             ("X-Polka-Response-DateTime", datetime.now(timezone.utc).isoformat())],
                        encode(value), "local")

    def common_error_response(self, status, message):
        # dump.cs: ApiError<T> keys Message=0, Error=1; IApiError union 4 is
        # CommonApiError, whose inherited Code=0 field is Unknown (enum value 0).
        # The client selects its dialog text by error code, not by Message.
        return Response(status, [("Content-Type", "application/x-msgpack"),
                                 ("X-Polka-Response-DateTime", datetime.now(timezone.utc).isoformat())],
                        encode([message, [4, [0]]]), "local-error")
