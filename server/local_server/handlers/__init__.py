"""Explicit local endpoints. Unregistered routes never claim business success."""
from .player import PlayerHandlers
from .login_bonus import LoginBonusHandlers
from ..services.login_bonus import LoginBonusService
from .passes import PassHandlers
from ..services.passes import PassService
from .home import HomeHandlers
from ..services.home import HomeService
from .present_box import PresentBoxHandlers
from ..services.present_box import PresentBoxService
from .timed import TimedHandlers
from ..services.timed import TimedService
from .shop import ShopHandlers
from ..services.shop import ShopService
from .character import CharacterHandlers
from ..services.character import CharacterService
from .quiz import QuizHandlers
from ..services.quiz import QuizService
from .lottery import LotteryHandlers
from ..services.lottery import LotteryService
from .box_lottery import BoxLotteryHandlers
from ..services.box_lottery import BoxLotteryService
from .stamina import StaminaHandlers
from ..services.stamina import StaminaService
from .story import StoryHandlers
from ..services.story import StoryService
from .quest import QuestHandlers
from ..services.quest import QuestService
from .chat import ChatHandlers
from ..services.chat import ChatService
from .guild import GuildHandlers
from ..services.guild import GuildService
from .box_item import BoxItemHandlers
from ..services.box_item import BoxItemService
from .event import EventHandlers
from ..services.event import EventService
from .arena import ArenaHandlers
from ..services.arena import ArenaService
from .garden import GardenHandlers
from ..services.garden import GardenService
from .magic_item import MagicItemHandlers
from ..services.magic_item import MagicItemService
from .dungeon2 import Dungeon2Handlers
from ..services.dungeon2 import Dungeon2Service
from .trial_battle import TrialBattleHandlers
from .climbing import ClimbingHandlers
from ..services.climbing import ClimbingService
from .tower import TowerHandlers
from ..services.tower import TowerService
from .skill_tree import SkillTreeHandlers
from ..services.skill_tree import SkillTreeService
from .blackjack import BlackjackHandlers
from ..services.blackjack import BlackjackService


class HandlerRegistry:
    def __init__(self, service, protocol, probability_source=None):
        player = PlayerHandlers(service, protocol)
        login_bonus = LoginBonusHandlers(LoginBonusService(service, protocol), protocol)
        passes = PassHandlers(PassService(service, protocol), protocol)
        home = HomeHandlers(HomeService(service, protocol), protocol)
        present_box = PresentBoxHandlers(PresentBoxService(service, protocol), protocol)
        timed = TimedHandlers(TimedService(service, protocol), protocol)
        shop = ShopHandlers(ShopService(service, protocol), protocol)
        character = CharacterHandlers(CharacterService(service, protocol), protocol)
        quiz = QuizHandlers(QuizService(service, protocol), protocol)
        lottery = LotteryHandlers(LotteryService(service, protocol, probability_source), protocol)
        box_lottery = BoxLotteryHandlers(BoxLotteryService(service, protocol), protocol)
        stamina = StaminaHandlers(StaminaService(service, protocol), protocol)
        story = StoryHandlers(StoryService(service, protocol), protocol)
        quest = QuestHandlers(QuestService(service, protocol), protocol)
        chat = ChatHandlers(ChatService(service, protocol), protocol)
        guild = GuildHandlers(GuildService(service, protocol), protocol)
        box_item = BoxItemHandlers(BoxItemService(service, protocol), protocol)
        event = EventHandlers(EventService(service, protocol, shop.service), protocol)
        arena = ArenaHandlers(ArenaService(service, protocol), protocol)
        garden = GardenHandlers(GardenService(service, protocol), protocol)
        magic_item = MagicItemHandlers(MagicItemService(service, protocol), protocol)
        dungeon2 = Dungeon2Handlers(Dungeon2Service(service, protocol), protocol)
        quest.dungeon2 = dungeon2.service
        self.dungeon2 = dungeon2.service
        trial_battle = TrialBattleHandlers(service.trial_battle, protocol)
        self.trial_battle = trial_battle.service
        self.lottery = lottery.service
        self.event = event.service
        climbing = ClimbingHandlers(ClimbingService(service, protocol), protocol)
        tower = TowerHandlers(TowerService(service, protocol), protocol)
        skill_tree = SkillTreeHandlers(SkillTreeService(service, protocol), protocol)
        blackjack = BlackjackHandlers(BlackjackService(service, protocol), protocol)
        self.routes = {
            "POST /blackjack/deal": blackjack.deal,
            "POST /blackjack/double": blackjack.double,
            "POST /blackjack/result": blackjack.result,
            "POST /tower/towertop": tower.top,
            "POST /tower/towerstart": tower.start,
            "POST /tower/towersetresult": tower.result,
            "POST /tower/gettowercontinueinfo": tower.continue_info,
            "POST /tower/resettowercontinueinfo": tower.reset,
            "POST /tower/gettowerguildmemberrank": tower.guild_rank,
            "POST /tower/gettowerfloorclearrate": tower.clear_rate,
            "POST /boxlottery/getboxlotteries": box_lottery.get,
            "POST /boxlottery/execboxlottery": box_lottery.execute,
            "POST /boxlottery/boxlotterynextsheet": box_lottery.next_sheet,
            "POST /skilltree/skilltreenoderelease": skill_tree.release,
            "POST /climbing/climbingtop": climbing.top,
            "POST /climbing/climbingstart": climbing.start,
            "POST /climbing/climbingresult": climbing.result,
            "POST /climbing/climbingrematching": climbing.rematching,
            "POST /climbing/climbingreset": climbing.reset,
            "POST /climbing/climbingbattlereset": climbing.battle_reset,
            "POST /dungeon2/getdungeon2info": dungeon2.info,
            "POST /dungeon2/getdungeon2hierarchyinfo": dungeon2.hierarchy,
            "POST /dungeon2/getdungeon2squareinfo": dungeon2.square,
            "POST /dungeon2/setdungeon2reset": dungeon2.reset,
            "POST /dungeon2/getdungeon2characterinfo": dungeon2.characters,
            "POST /dungeon2/getdungeon2enemyinfo": dungeon2.enemies,
            "POST /dungeon2/setdungeon2battlestatus": dungeon2.status,
            "POST /dungeon2/getdungeon2iteminfo": dungeon2.items,
            "POST /dungeon2/setdungeon2squarecomplete": dungeon2.complete,
            "POST /trialbattle/deleteunavailabletrialbattlerentalcharacter": trial_battle.delete_unavailable_rentals,
            "POST /magicitem/makemagicitem": magic_item.create,
            "POST /magicitem/magicitemlevelup": magic_item.levelup,
            "POST /garden/gardentop": garden.top,
            "POST /garden/receivegardenproducts": garden.receive,
            "POST /garden/gardenbuildinglevelup": garden.levelup,
            "POST /garden/updategardenworker": garden.workers,
            "POST /garden/searchinventorychange": garden.search,
            "POST /garden/timeacceleration": garden.accelerate,
            "POST /room/roomtop": garden.room,
            "POST /arena/arenagetinfo": arena.info,
            "POST /arena/arenagetenemyinfos": arena.enemies,
            "POST /arena/arenagetrankinginfos": arena.rankings,
            "POST /arena/arenagethistoryinfos": arena.histories,
            "POST /event/eventtop": event.top,
            "POST /event/geteventdamageranking": event.damage_ranking,
            "POST /subevent/subeventtop": event.sub_top,
            "POST /boxitem/openboxitem": box_item.open,
            "POST /guild/getguildinfo": guild.get,
            "POST /guild/searchguild": guild.search,
            "POST /quest/queststart": quest.start,
            "POST /quest/setquestresult": quest.result,
            "POST /quest/questskip": quest.skip,
            "POST /quest/recoverquestchallengecount": quest.recover_quest,
            "POST /quest/recoverquestgroupchallengecount": quest.recover_group,
            "POST /chatapi/getopenchatroommembercount": chat.member_counts,
            "POST /chatapi/getlogcount": chat.log_count,
            "POST /chatapi/getroomchatlog": chat.room_logs,
            "POST /chatapi/getroomchatlogfrombottom": chat.room_logs_from_bottom,
            "POST /stamina/recoverstamina": stamina.recover,
            "POST /story/readstory": story.read,
            "POST /story/openstory": story.open,
            "POST /quiz/answerquiz": quiz.answer,
            "POST /character/levelup": character.levelup,
            "POST /character/updatefavorite": character.favorite,
            "POST /character/levelupselectedcharacters": character.levelup_selected,
            "POST /character/rankup": character.rankup,
            "POST /character/rarityup": character.rarityup,
            "POST /character/limitbreak": character.limitbreak,
            "POST /equipment/setequipments": character.equip,
            "POST /equipment/setequipmentsauto": character.equip_auto,
            "POST /equipment/makeequipment": character.make_equipment,
            "POST /user/userlogin": player.login,
            "POST /user/andappuserlogin": player.login,
            "POST /user/dmmuserlogin": player.login,
            "POST /user/steamuserlogin": player.login,
            "POST /user/checkssgaccountassociation": player.association,
            "POST /user/agreetotermsofservice": player.agreement,
            "POST /user/settutorialprogress": player.tutorial,
            "POST /user/getuserstone": shop.user_stone,
            "POST /gametop/getgametopinfo": shop.game_top,
            "POST /loginbonus/getloginbonus": login_bonus.get,
            "POST /shop/updateshoppassrepurchasenotification": passes.shop_notifications,
            "POST /shop/getshops": shop.get,
            "POST /shop/purchaseshoppackage": shop.package,
            "POST /shop/purchaseshoplineups": shop.lineups,
            "POST /shop/updateshoplineup": shop.update_lineup,
            "POST /shop/verifypaymentproduct": shop.verify,
            "POST /shop/updateinventoryafterpurchase": shop.payment,
            "POST /shop/updateinventoryafterexternalpurchase": shop.external_refresh,
            "POST /battlepass/getbattlepasses": passes.battle_passes,
            "POST /battlepass/battlepassreceiverewards": passes.receive_rewards,
            "POST /battlepass/battlelevelpurchase": passes.purchase_levels,
            "POST /presentbox/getpresentboxinfo": present_box.get,
            "POST /presentbox/receivepresents": present_box.receive,
            "POST /home/sethomecharacter": home.set_character,
            "POST /mission/receiverewards": timed.receive_missions,
            "POST /lottery/getlotteries": lottery.get,
            "POST /lottery/execlottery": lottery.execute,
            "POST /lottery/getlotteryhistories": lottery.histories,
            "POST /lottery/getlotterywinningchance": lottery.chances,
            "POST /lottery/setlotterycharacterselect": lottery.select,
            "POST /party/getparties": player.parties,
            "POST /party/saveparties": player.save_parties,
            "POST /party/setpartyname": player.party_name,
            "POST /profile/getprofileinfo": player.profile,
            "POST /profile/updateprofile": player.update_profile,
        }

    def dispatch(self, request):
        handler = self.routes.get(request.method + " " + request.path)
        return handler(request) if handler else None
