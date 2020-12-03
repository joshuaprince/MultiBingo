import json
from datetime import timedelta
from typing import Optional

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.db.models import Q
from django.utils import timezone

from backend.models import PlayerBoard, Board


class BoardChangeConsumer(AsyncJsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game_code = None
        self.board_id = None
        self.player_name = None  # Remains None if this represents a Spectator
        self.player_board_id = None  # Remains None if this represents a Spectator

    async def connect(self):
        self.game_code = self.scope['url_route']['kwargs']['game_code']
        self.player_name = self.scope['url_route']['kwargs'].get('player_name')

        board_obj, player_board_obj = \
            await get_board_and_player_board(self.game_code, self.player_name)
        if not board_obj:
            print(f"Error getting board: {self.game_code} (player: {self.player_name})")
            return  # reject connection

        self.board_id = board_obj.pk
        if player_board_obj:
            self.player_board_id = player_board_obj.pk

        await self.channel_layer.group_add(
            self.game_code,
            self.channel_name
        )

        await self.accept()

        if self.player_board_id is not None:
            await mark_disconnected(self.player_board_id, False)

        await self.send_boards_all_consumers()

        print(f"{self.player_name if self.player_name else 'Spectator'} joined game {self.game_code}.")

    async def receive(self, text_data: str = None, **kwargs):
        broadcast_boards = False
        text_data_json = json.loads(text_data)
        action = text_data_json.get('action')

        if action == 'board_mark' and self.player_board_id:
            pos = int(text_data_json['position'])
            to_state = int(text_data_json['to_state'])
            await self.rx_mark_board(pos, to_state)
            broadcast_boards = True

        if broadcast_boards:
            await self.send_boards_all_consumers()
        else:
            # only send to the client that sent this message (i.e. for a ping)
            await self.send_boards_to_ws()

    async def rx_mark_board(self, pos, to_state):
        await mark_square(self.player_board_id, pos, to_state)
        await mark_disconnected(self.player_board_id, False)

    async def disconnect(self, code):
        await self.channel_layer.group_discard(
            self.game_code,
            self.channel_name
        )

        if self.player_board_id is not None:
            await mark_disconnected(self.player_board_id, True)
            await self.send_boards_all_consumers()

        print(f"{self.player_name if self.player_name else 'Spectator'} disconnected from game {self.game_code}.")

    async def send_boards_all_consumers(self):
        await self.channel_layer.group_send(
            self.game_code, {
                'type': 'send_boards_to_ws'
            }
        )

    async def send_boards_to_ws(self, event=None):
        board_states = await get_board_states(self.board_id)
        await self.send(text_data=json.dumps(board_states))


@database_sync_to_async
def get_board_states(board_id: int):
    # Only sends board states of players who are not disconnected
    recent_dc_time = timezone.now() - timedelta(minutes=1)
    pboards = PlayerBoard.objects.filter(
        Q(disconnected_at=None) | Q(disconnected_at__gt=recent_dc_time),
        board_id=board_id
    )
    data = [{
        'player_name': pb.player_name,
        'board': pb.squares,
        'disconnected_at': pb.disconnected_at.isoformat() if pb.disconnected_at else None,
    } for pb in pboards]
    return data


@database_sync_to_async
def get_board_and_player_board(game_code: str, player: Optional[str]) -> (Board, PlayerBoard):
    board = Board.objects.filter(seed=game_code).first()
    if not board:
        return None, None

    if player:
        player_board_obj = PlayerBoard.objects.filter(board_id=board.pk, player_name=player).first()
    else:
        player_board_obj = None

    return board, player_board_obj


@database_sync_to_async
def mark_square(player_board_id: int, pos: int, to_state: int):
    player_board_obj = PlayerBoard.objects.get(pk=player_board_id)
    player_board_obj.mark_square(pos, to_state)
    player_board_obj.save()
    print(f"Updated board for {player_board_obj.player_name}")


@database_sync_to_async
def mark_disconnected(player_board_id: int, disconnected: bool):
    player_board_obj = PlayerBoard.objects.get(pk=player_board_id)
    player_board_obj.disconnected_at = timezone.now() if disconnected else None
    player_board_obj.save()
