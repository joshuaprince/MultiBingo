from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from backend.models.color import Color
from backend.models.player_board_marking import PlayerBoardMarking


class PlayerBoard(models.Model):
    """
    A player's set of markings on a particular game board.
    """
    id = models.AutoField(primary_key=True)
    board = models.ForeignKey('Board', on_delete=models.CASCADE)
    player_name = models.CharField(blank=False, db_index=True, max_length=128)
    markings = models.ManyToManyField('Space', through='PlayerBoardMarking')
    disconnected_at = models.DateTimeField(null=True)

    def __str__(self):
        return str(self.board) + " : " + self.player_name

    class Meta:
        unique_together = ['board', 'player_name']

    def mark_space(self, space_id: int, to_state: Color = None, covert_marked: bool = None,
                   as_player: bool = False):
        """
        Mark a space on this player's board to a specified state.
        :return: (changed, announce) - a pair of booleans that indicate whether the board was
                 changed and whether it should be announced.
        """
        marking = self.playerboardmarking_set.get(space_id=space_id)

        if not as_player and marking.marked_by_player:
            return False, False

        changed = False
        if to_state is not None and marking.color != to_state:
            marking.color = to_state
            changed = True
        if covert_marked is not None and marking.covert_marked != covert_marked:
            marking.covert_marked = covert_marked
            changed = True
        if to_state is not None and as_player:
            marking.marked_by_player = True
            changed = True

        announce = False
        if changed and to_state in [Color.COMPLETE, Color.INVALIDATED] and not marking.announced:
            marking.announced = True
            announce = True

        if changed:
            marking.save()

        return changed, announce


@receiver(post_save, sender=PlayerBoard)
def build_player_board(instance: PlayerBoard, created: bool, **kwargs):
    if created:
        print(f"Created a new player board with game code {instance.board.game_code}, "
              f"player {instance.player_name}")

        for space in instance.board.space_set.order_by('position').all():
            PlayerBoardMarking.objects.create(
                space=space,
                player_board=instance,
                color=space.initial_state(),
            )
