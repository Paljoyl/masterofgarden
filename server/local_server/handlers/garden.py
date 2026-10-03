"""Validate garden wire requests; clients never supply time or building levels."""
from ..protocol import integer, sequence, LocalError


class GardenHandlers:
    def __init__(self, service, protocol):
        self.service, self.protocol = service, protocol

    def top(self, request):
        self.protocol.empty_request(request)
        return self.protocol.response(request, self.service.run(request, 'top'))

    def receive(self, request):
        fields = self.protocol.request(request)
        codes = [integer(code, minimum=1) for code in sequence(fields['BuildingCodes'], maximum=100)]
        if len(set(codes)) != len(codes):
            raise LocalError('local_garden_duplicate_buildings')
        return self.protocol.response(request, self.service.run(request, 'receive', codes))

    def levelup(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['BuildingCode'], minimum=1)
        return self.protocol.response(request, self.service.run(request, 'levelup', code))

    def workers(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['BuildingCode'], minimum=1)
        count = integer(fields['WorkerCount'], maximum=2**31 - 1)
        return self.protocol.response(request, self.service.run(request, 'workers', code, count))

    def search(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['BuildingCode'], minimum=1)
        target = integer(fields['InventoryCode'], minimum=1)
        return self.protocol.response(request, self.service.run(request, 'search', code, target))

    def accelerate(self, request):
        fields = self.protocol.request(request)
        items = {}
        for value in sequence(fields['StackItems'], maximum=100):
            row = self.protocol.fields('StackItemInfo', value, strict=True)
            code = integer(row['ItemCode'], minimum=1)
            count = integer(row['Count'], minimum=1, maximum=2**31 - 1)
            integer(row['RecoveredAt'])  # Validated but never used as a clock.
            if code in items:
                raise LocalError('local_garden_duplicate_items')
            items[code] = count
        if not items:
            raise LocalError('local_garden_acceleration_items_required')
        return self.protocol.response(request, self.service.run(request, 'accelerate', items))

    def room(self, request):
        fields = self.protocol.request(request)
        code = integer(fields['RoomCode'], minimum=1)
        mode = integer(fields['RoomTimeModeIndex'], maximum=1)
        return self.protocol.response(request, self.service.run(request, 'room', code, mode))
