"""Read-only response fields shared by local reward operations."""
from ..protocol import integer

FREE_STONE = 990000001
SUPPLEMENT_PAID_STONE = 990000002
PAID_STONE = 990000003  # TW PC: ItemCodes.PaidStoneCode selects behaviour type 7.
STONE_CODES = (FREE_STONE, SUPPLEMENT_PAID_STONE, PAID_STONE)


def stone_items(protocol, state):
    owned = {protocol.fields('StackItemInfo', row)['ItemCode']: row for row in state['StackItems']}
    return [owned.get(code) or protocol.model('StackItemInfo', {
        'ItemCode': code, 'Count': 0, 'RecoveredAt': 0}) for code in STONE_CODES]


def inventory_update(protocol, state, changed_codes=()):
    user = protocol.fields('UserInfo', state['User'])
    changed_codes = set(changed_codes)
    if user['Stamina'] is not None:
        # The stamina model also reads behaviour type 19 from StackItems. Send
        # its absolute balance/time even for direct stamina rewards (RewardType 4).
        changed_codes.add(390000002)
    items = [item for item in state['StackItems'] if item[0] in changed_codes]
    if changed_codes.intersection(STONE_CODES):
        # The client calculates paid balance from two pools when either changes.
        # Send both absolute balances, including zero, along with the free balance.
        items = [item for item in items if item[0] not in STONE_CODES] + stone_items(protocol, state)
    return protocol.model('InventoryUpdateInfo', {
        'Characters': [row for row in state['Characters'] if row[0] in changed_codes], 'MagicItems': [],
        'StackItems': items,
        'Honors': state.get('Honors', []), 'ShopPassInfos': state.get('ShopPassInfos', []), 'Stamina': user['Stamina'],
        'SomeItemsAreSendToPresentBox': False,
    })


def total_battle_power(players, protocol, session):
    # Match the local home baseline until a verified power formula is available.
    template = players.templates.get((session.player_id, session.variant, '/gametop/getgametopinfo'))
    if template is None:
        return 0
    value = protocol.fields('GetGameTopInfoResponse', template)['TotalBattlePower']
    return integer(value) if value is not None else 0
