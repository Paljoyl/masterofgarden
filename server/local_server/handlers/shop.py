"""Shop wire validation and local transaction error mapping."""
from PostgreSQL.players import InsufficientItems, OperationConflict
from PostgreSQL.player_protocol import InvalidPlayerData
from mog_protocol.codec import EMPTY
from ..protocol import LocalError, integer, sequence


class ShopHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def _call(self, request, callback, *, raw=False):
        try:
            result = callback()
        except InsufficientItems as exc:
            raise LocalError('local_shop_insufficient_items', 409) from exc
        except OperationConflict as exc:
            raise LocalError('local_shop_state_conflict', 409) from exc
        except InvalidPlayerData as exc:
            raise LocalError('local_shop_reward_definition_invalid', 503) from exc
        return self.protocol.response(request, value=result) if raw else self.protocol.response(request, result)

    def get(self, request):
        fields = self.protocol.request(request)
        categories = [integer(v, maximum=10) for v in sequence(fields['ShopCategories'], maximum=11)]
        event = integer(fields['EventCode'])
        return self._call(request, lambda: self.service.get(request, set(categories), event))

    def package(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['ShopPackageCode'], minimum=1)
        return self._call(request, lambda: self.service.package(request, code))

    def lineups(self, request):
        fields = self.protocol.request(request)
        purchases = []
        for value in sequence(fields['PurchaseShopLineups'], maximum=100):
            row = self.protocol.fields('PurchaseShopLineupInfo', value, strict=True)
            purchases.append((integer(row['ShopLineupCode'], minimum=1), integer(row['Count'], minimum=1, maximum=2**31 - 1)))
        if len({c for c, _ in purchases}) != len(purchases):
            raise LocalError('duplicate_shop_lineup')
        return self._call(request, lambda: self.service.lineups(request, purchases))

    def verify(self, request):
        fields = self.protocol.request(request)
        codes = [integer(c, minimum=1) for c in sequence(fields['ShopPaymentCodes'], maximum=100)]
        if len(set(codes)) != len(codes):
            raise LocalError('duplicate_shop_payment_code')
        self.service.verify(request, codes)
        # IShopApi declares UniTask without a response model; successful capture body is empty.
        return self.protocol.response(request, value=EMPTY)

    def update_lineup(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['ShopCode'], minimum=1)
        return self._call(request, lambda: self.service.update_lineup(request, code))

    def payment(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['ShopPaymentCode'], minimum=1)
        if type(fields['IncludePaidStone']) is not bool:
            raise LocalError('invalid_include_paid_stone')
        return self._call(request, lambda: self.service.payment(request, code), raw=True)

    def external_refresh(self, request):
        self.protocol.empty_request(request)
        return self._call(request, lambda: self.service.external_refresh(request))

    def user_stone(self, request):
        self.protocol.empty_request(request)
        return self._call(request, lambda: self.service.user_stone(request))

    def game_top(self, request):
        self.protocol.request(request)
        return self._call(request, lambda: self.service.game_top(request), raw=True)
