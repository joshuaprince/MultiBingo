import json
from abc import ABC, abstractmethod
from random import randrange
from typing import Set, Dict

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from backend.log_consumer_exceptions import log_consumer_exceptions
from backend.models import Color, Space
from backend.models.board import Board
from backend.models.player_board import PlayerBoard
from backend.models.player_board_marking import PlayerBoardMarking
from backend.serializers.board_player import BoardPlayerSerializer
from backend.serializers.board_plugin import BoardPluginSerializer
from backend.serializers.message_relay import MessageRelaySerializer
from backend.serializers.player_board import PlayerBoardSerializer
from generation.board_generator import generate_board
from generation.goals import ConcreteGoal
from win_detection.win_detection import winning_space_ids


@log_consumer_exceptions
class BaseWebConsumer(AsyncJsonWebsocketConsumer, ABC):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_actions = []
        self.game_code = None
        self.client_id = None  # Player Name if a player; unique ID if otherwise
        self.board_id = None

        # Optional - only set if this is representative of a single Player and not a Spectator
        self.player_board_id = None  # Remains None if this represents a Spectator

    async def connect(self):
        self.game_code = self.scope['url_route']['kwargs']['game_code']

        self.board_id = await get_board_id(self.game_code)
        if not self.board_id:
            print(f"Error getting board: {self.game_code} (client: {self.client_id})")
            return  # reject connection

        await self.channel_layer.group_add(self.game_code, self.channel_name)
        await self.accept()
        await self.send_board_to_ws()
        await self.send_pboards_all_consumers()

    async def receive(self, text_data: str = None, **kwargs):
        broadcast_board = False
        broadcast_pboards = False
        text_data_json = json.loads(text_data)
        action = text_data_json.get('action')

        if action not in self.allowed_actions:
            print(f"WebSocket {self.client_id} attempted disallowed action {{{action}}}")
            return

        if action == 'board_mark' and self.player_board_id:
            space_id = int(text_data_json['space_id'])
            to_state = text_data_json.get('to_state')
            covert_marked = text_data_json.get('covert_marked')
            broadcast_pboards = await self.rx_mark_board_player(space_id, to_state, covert_marked)

        if action == 'board_mark_admin':
            space_id = int(text_data_json['space_id'])
            to_state = int(text_data_json['to_state'])
            player_name = text_data_json['player']
            broadcast_pboards = await self.rx_mark_board_admin(space_id, to_state, player_name)

        if action == 'game_state':
            to_state = text_data_json['to_state']
            await self.rx_game_state(to_state)

        if action == 'reveal_board':
            revealed = await self.rx_reveal_board()
            if revealed:
                broadcast_board = True
                broadcast_pboards = True

        if action == 'set_automarks':
            space_ids = text_data_json['space_ids']
            changed = await self.rx_set_automarks(space_ids)
            if changed:
                broadcast_board = True

        if action == 'message_relay':
            content_mc_tellraw = text_data_json.get('json')
            msg = MessageRelaySerializer({
                'sender': self.client_id,
                'json': content_mc_tellraw,
            })
            await self.send_message_relay_all_consumers(msg.data)

        if action == 'plugin_parity':
            my_settings = text_data_json.get('my_settings')
            is_echo = text_data_json.get('is_echo')
            await self.send_plugin_parity_all_consumers({
                'sender': self.client_id,
                'is_echo': is_echo,
                'settings': my_settings,
            })

        if broadcast_board:
            await self.send_board_all_consumers()

        if broadcast_pboards:
            await self.send_pboards_all_consumers()
        else:
            # only send to the client that sent this message (i.e. for a ping)
            await self.send_pboards_to_ws()

    async def disconnect(self, code):
        # Clear all automarkings since this client is no longer connected
        had_automarks = await set_automarks(self.board_id, self.client_id, {})
        if had_automarks:
            await self.send_board_all_consumers()

        await self.channel_layer.group_discard(
            self.game_code,
            self.channel_name
        )

    async def rx_mark_board_player(self, space_id, to_state: int = None, covert_marked: int = None):
        changed, game_state_msg, winner = await mark_space_player(
            self.player_board_id, space_id, to_state, covert_marked)
        await mark_disconnected(self.player_board_id, False)
        if game_state_msg is not None:
            await self.send_game_state_all_consumers(game_state_msg)
        if winner:
            await self.send_game_state_all_consumers({'state': 'end', 'winner': winner})
        return changed

    async def rx_mark_board_admin(self, space_id, to_state, player):
        changed, game_state_msg, winner = await mark_space_admin(
            self.board_id, player, space_id, to_state)
        if game_state_msg is not None:
            await self.send_game_state_all_consumers(game_state_msg)
        if winner:
            await self.send_game_state_all_consumers({'state': 'end', 'winner': winner})
        return changed

    async def rx_game_state(self, to_state):
        valid_states = ['start', 'end']
        if to_state in valid_states:
            await self.send_game_state_all_consumers({'state': to_state})

    async def rx_reveal_board(self):
        changed = await reveal_board(self.board_id)
        return changed

    async def rx_set_automarks(self, space_ids):
        changed = await set_automarks(self.board_id, self.client_id, space_ids)
        return changed

    async def send_board_all_consumers(self):
        await self.channel_layer.group_send(
            self.game_code, {
                'type': 'send_board_to_ws'
            }
        )

    @abstractmethod
    async def send_board_to_ws(self, event=None):
        # Board format depends on Consumer type. Override in child consumers.
        ...

    async def send_pboards_all_consumers(self):
        await self.channel_layer.group_send(
            self.game_code, {
                'type': 'send_pboards_to_ws'
            }
        )

    async def send_pboards_to_ws(self, event=None):
        board_states = await database_sync_to_async(PlayerBoardSerializer.from_board_id)(
            self.board_id, self.player_board_id
        )
        await self.send(text_data=json.dumps(board_states))

    async def send_game_state_all_consumers(self, game_state):
        await self.channel_layer.group_send(
            self.game_code, {
                'type': 'send_game_state_to_ws',
                'game_state': game_state,
            }
        )

    async def send_game_state_to_ws(self, event=None):
        await self.send(text_data=json.dumps({
            'game_state': event['game_state']
        }))

    async def send_message_relay_all_consumers(self, message):
        await self.channel_layer.group_send(
            self.game_code, {
                'type': 'send_message_relay_to_ws',
                'message': message,
            }
        )

    async def send_message_relay_to_ws(self, event=None):
        await self.send(text_data=json.dumps({
            'message_relay': event['message']
        }))

    async def send_plugin_parity_all_consumers(self, message):
        await self.channel_layer.group_send(
            self.game_code, {
                'type': 'send_plugin_parity_to_ws',
                'message': message,
            }
        )

    async def send_plugin_parity_to_ws(self, event=None):
        await self.send(text_data=json.dumps({
            'plugin_parity': event['message']
        }))


@log_consumer_exceptions
class PlayerWebConsumer(BaseWebConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_actions = [
            'board_mark',
            'reveal_board',
            # 'message',
        ]

    async def connect(self):
        await super().connect()
        self.client_id = self.scope['url_route']['kwargs'].get('player_name')

        if self.client_id:
            player_board_obj = (await database_sync_to_async(PlayerBoard.objects.get_or_create)(
                board_id=self.board_id, player_name=self.client_id
            ))[0]
            self.player_board_id = player_board_obj.pk
            await mark_disconnected(self.player_board_id, False)

            # Need to send board with Auto Mark indicators now that player_board_id is set
            await self.send_board_to_ws()
        else:
            # This is a spectator. Give them a unique identifier.
            self.client_id = f'[Spectator {randrange(9999)}]'

        print(f"{self.client_id} joined game {self.game_code}.")

    async def disconnect(self, code):
        await super().disconnect(code)
        if self.player_board_id is not None:
            await mark_disconnected(self.player_board_id, True)
            await self.send_pboards_all_consumers()

        print(f"{self.client_id} disconnected from game {self.game_code}.")

    async def send_board_to_ws(self, event=None):
        board = await database_sync_to_async(BoardPlayerSerializer.from_id)(
            self.board_id, self.player_board_id
        )
        await self.send(text_data=json.dumps({
            'board': board,
        }))


@log_consumer_exceptions
class PluginBackendConsumer(BaseWebConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_actions = [
            'board_mark_admin',
            'game_state',
            'reveal_board',
            'set_automarks',
            'message_relay',
            'plugin_parity',
        ]

    async def connect(self):
        await super().connect()
        self.client_id = self.scope['url_route']['kwargs'].get('client_id')
        print(f"{{{self.client_id}}} joined game {self.game_code}.")

    async def disconnect(self, code):
        await super().disconnect(code)
        print(f"{{{self.client_id}}} disconnected from game {self.game_code}.")

    async def send_board_to_ws(self, event=None):
        board = await database_sync_to_async(BoardPluginSerializer.from_id)(self.board_id)
        await self.send(text_data=json.dumps({
            'board': board,
        }))


@database_sync_to_async
def get_board_id(game_code: str):
    try:
        return Board.objects.get(game_code=game_code).pk
    except Board.DoesNotExist:
        return generate_board(game_code).pk


@database_sync_to_async
def reveal_board(board_id: str, revealed: bool = True):
    """
    Reveal the board for all players.
    :return: True if the board reveal state changed, False otherwise.
    """
    board = Board.objects.filter(pk=board_id).first()
    if not board:
        print("Tried to reveal nonexisting board ID: " + board_id)
        return

    new_obscured = not revealed
    if board.obscured != new_obscured:
        board.obscured = not revealed
        board.save()
        return True
    else:
        return False


@database_sync_to_async
def mark_space_player(player_board_id: int, space_id: int,
               to_state: int = None, covert_marked: bool = None):
    """
    Mark a space on a player's board.
    :return: (changed, announcement) - changed is a bool that indicates whether the board was
             changed with this marking. announcement is an optional object that contains the
             announcement that should be made, if any.
    """
    player_board_obj = PlayerBoard.objects.select_related('board').get(pk=player_board_id)
    changed, announce = player_board_obj.mark_space(
        space_id, to_state, covert_marked, as_player=True)

    winner = None
    if player_board_obj.board.winner is None and winning_space_ids(player_board_obj):
        winner = player_board_obj.player_name
        player_board_obj.board.winner = player_board_obj
        player_board_obj.board.save()

    if announce:
        space = Space.objects.get(pk=space_id)
        game_state = {
            'state': 'marking',
            'marking_type': 'invalidate' if Color(to_state) == Color.INVALIDATED else 'complete',
            'player': player_board_obj.player_name,
            'goal': ConcreteGoal.from_space(space).description(),
        }
        return changed, game_state, winner
    else:
        return changed, None, winner


@database_sync_to_async
def mark_space_admin(board_id: int, player_name: str, space_id: int, to_state: int):
    """
    Mark a space on a player's board.
    :return: (changed, announce) - a pair of booleans that indicate whether the board was
             changed and whether it should be announced.
    """
    player_board_obj = PlayerBoard.objects.get_or_create(board_id=board_id, player_name=player_name)[0]
    changed, announce = player_board_obj.mark_space(space_id, to_state)

    winner = None
    if player_board_obj.board.winner is None and winning_space_ids(player_board_obj):
        winner = player_board_obj.player_name
        player_board_obj.board.winner = player_board_obj
        player_board_obj.board.save()

    if announce:
        space = Space.objects.get(pk=space_id)
        game_state = {
            'state': 'marking',
            'marking_type': 'invalidate' if Color(to_state) == Color.INVALIDATED else 'complete',
            'player': player_board_obj.player_name,
            'goal': ConcreteGoal.from_space(space).description(),
        }
        return changed, game_state, winner
    else:
        return changed, None, winner


@database_sync_to_async
def mark_disconnected(player_board_id: int, disconnected: bool):
    player_board_obj = PlayerBoard.objects.get(pk=player_board_id)
    player_board_obj.disconnected_at = timezone.now() if disconnected else None
    player_board_obj.save()


@database_sync_to_async
def set_automarks(board_id: int, client_id: str, player_space_ids_map: Dict[str, Set[str]]):
    changed = False

    # Cross = All combinations of (player name, space ID) tuples in the map
    current_automark_pbms = (PlayerBoardMarking.objects
                             .filter(player_board__board_id=board_id, auto_marker_client_id=client_id)
                             .select_related('player_board'))
    current_cross = set((a.player_board.player_name, a.space_id) for a in current_automark_pbms)

    new_cross = set((pname, spcid) for pname, pset in player_space_ids_map.items() for spcid in pset)

    # Create missing AutoMarks
    for player_name, space_id in new_cross.difference(current_cross):
        player_board = PlayerBoard.objects.get_or_create(board_id=board_id, player_name=player_name)[0]
        PlayerBoardMarking.objects.filter(
            player_board=player_board, space_id=space_id
        ).update(auto_marker_client_id=client_id)
        changed = True

    # Delete removed AutoMarks
    for player_name, space_id in current_cross.difference(new_cross):
        current_automark_pbms.filter(
            player_board__player_name=player_name, space_id=space_id
        ).update(auto_marker_client_id='')
        changed = True

    return changed
