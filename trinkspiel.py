#!/usr/bin/env python
import random


class Player(object):

    ALL_PLAYERS = []

    def __init__(self, name, coins, clothing_pieces, age, sex):
        self.name = name
        self.board_position = 0
        self.sips = 0
        self.coins = coins
        self.clothing_pieces = clothing_pieces
        self.player_position = len(self.ALL_PLAYERS)
        self.age = age
        self.sex = sex
        self.ALL_PLAYERS.append(self)
        self.last_roll = None
        self.skip_next_turn = False

    @classmethod
    def randomize(cls, name, sex):
        """Creates a randomized Player instance"""
        kwargs = {
            'coins': random.randint(0, 10),  # FIXME: Should be biased towards 0
            'clothing_pieces': random.randint(5, 12),
            'sex': sex,
            'age': random.randint(18, 37),
        }
        return Player(name=name, **kwargs)

    @classmethod
    def all_players(cls):
        return cls.ALL_PLAYERS

    def left_neighbor(self):
        return self.ALL_PLAYERS[self.player_position-1]

    def right_neighbor(self):
        return self.ALL_PLAYERS[(self.player_position+1) % len(self.ALL_PLAYERS)]

    def take_turn(self):
        # Roll the dice
        roll = self.last_roll = random.randint(1, 6)
        print("%s rolled a %s" % (self, roll))
        self.move(rel=roll)

    def drink(self, sips):
        self.sips += sips
        print("%s drank %s" % (self, sips))

    def strip(self):
        if self.clothing_pieces == 1:
            print("Player %s is now naked!" % (self))
        self.clothing_pieces = max(0, self.clothing_pieces - 1)
        print("%s stripped" % (self))

    def move(self, rel=None, abs=None):
        if rel:
            self.board_position = self.board_position + rel
        else:
            self.board_position = abs
        print("%s moved to %s" % (self, self.board_position))
        self.apply_tile_effect()

    def skip_next_turn(self):
        self.skip_next_turn = True

    def apply_tile_effect(self):
        tile = BOARD[self.board_position]
        tile.apply_effects(self)

    def __repr__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"<Player %s '%s'>" % (self.player_position, self.name)


class Tile(object):

    def __init__(self, name, change_pos_abs=None, change_pos_rel=None, sips=0, lose_clothing=False):
        self.name = name
        self.sips = sips
        self.change_pos_rel = change_pos_rel
        self.change_pos_abs = change_pos_abs
        self.lose_clothing = lose_clothing

    def apply_effects(self, player):
        if callable(self.sips):
            # Sips depends on what the player rolled
            player.drink(self.sips(player.last_roll()))
        elif self.sips > 0:
            player.drink(self.sips)
        if self.change_pos_rel:
            player.move(rel=self.change_pos_rel)
        if self.change_pos_abs:
            player.move(abs=self.change_pos_abs)
        if self.lose_clothing:
            player.strip()


class NoOpTile(Tile):
    """Tile that does nothing"""
    def __init__(self, name):
        return super(NoOpTile, self).__init__(name)


class NeighborEffectTile(Tile):
    """Tile that applies its effects to the player and his/her two neighbors"""
    def __init__(self, *args, **kwargs):
        self.exclude_self = kwargs.pop('exclude_self', False)
        self.exclude_left = kwargs.pop('exclude_left', False)
        self.exclude_right = kwargs.pop('exclude_right', False)
        return super(NeighborEffectTile, self).__init__(*args, **kwargs)

    def apply_effects(self, player):
        # Apply effects to neighbors
        apply_to = []
        if not self.exclude_self:
            apply_to.append(player)
        if not self.exclude_left:
            apply_to.append(player.left_neighbor())
        if not self.exclude_right:
            apply_to.append(player.right_neighbor())

        for p in apply_to:
            return super(NeighborEffectTile, self).apply_effects(p)


class EverybodyEffectTile(Tile):
    """Tile that applies its effects to everybody"""
    def __init__(self, *args, **kwargs):
        self.exclude_self = kwargs.pop('exclude_self', False)
        self.closest_start_goal = kwargs.pop('closest_start_goal', False)
        self.only_sex = kwargs.pop('only_sex', None)
        self.has_siblings = kwargs.pop('has_siblings', None)
        self.has_age = kwargs.pop('has_age', None)
        self.max_has_cash = kwargs.pop('max_has_cash', None)
        self.max_age = kwargs.pop('max_age', None)
        self.has_glasses = kwargs.pop('has_glasses', None)
        self.wears_jeans = kwargs.pop('wears_jeans', None)
        return super(EverybodyEffectTile, self).__init__(*args, **kwargs)

    def players_closest_start_goal(self, player):
        all_players = player.all_players()
        p1 = all_players[0]

        min_pos = max_pos = p1.board_position
        min_players = [p1]
        max_players = [p1]

        for p in all_players[1:]:
            if p.board_position <= min_pos:
                min_players = [p] if p.board_position == min_pos else min_players + [p]
                min_pos = p.board_position
            if p.board_position >= max_pos:
                max_players = [p] if p.board_position == max_pos else max_players + [p]
                max_pos = p.board_position

        return min_players + max_players

    def apply_effects(self, player):
        # Apply effects to all players instead of the given one
        if self.closest_start_goal:
            apply_to = self.players_closest_start_goal()
        else:
            apply_to = player.all_players()

        if self.exclude_self:
            apply_to.remove(player)

        for p in apply_to:
            super(EverybodyEffectTile, self).apply_effects(p)


class SingTile(EverybodyEffectTile):
    pass


class SkipNextTurnTile(Tile):
    """Skips the next turn for this player"""
    def apply_effects(self, player):
        super(SkipNextTurnTile).apply_effects(player)
        player.skip_next_turn()


class RollAgainTile(Tile):
    """Take an extra turn for this player"""
    def apply_effects(self, player):
        super(RollAgainTile, self).apply_effects(player)
        player.take_turn()


class FixmeTile(Tile):
    def apply_effects(self, player):
        raise NotImplementedError("Tile '%s' is not yet implemented" % (self.name))


class ChoiceTile(FixmeTile):
    """Tile that applies its effects to everybody"""
    def __init__(self, *args, **kwargs):
        self.num_players = kwargs.pop('num_players')
        self.only_sex = kwargs.pop('only_sex', None)
        super(ChoiceTile, self).__init__(*args, **kwargs)


class WinTile(NoOpTile):
    def apply_effects(self, player):
        raise NotImplementedError("Invalid condition - %s appears to have won." % (player))

BOARD = [
    NoOpTile('START'),
    EverybodyEffectTile('1', sips=1),
    NeighborEffectTile('2', sips=2),
    Tile('3', change_pos_rel=-2),
    SingTile('4', sips=2),  # FIXME
    Tile('5', change_pos_abs=32, sips=1),
    Tile('6', sips=1),
    EverybodyEffectTile('7', exclude_self=True, sips=1),
    NoOpTile('8'),
    ChoiceTile('9', num_players=1, sips=1),
    EverybodyEffectTile('10', only_sex='M', sips=1),
    NeighborEffectTile('11', exclude_left=True, sips=1),
    ChoiceTile('12', num_players=1, sips=2),
    Tile('13', change_pos_abs=0, sips=lambda d: d),
    EverybodyEffectTile('14', closest_start_goal=True, sips=1),
    ChoiceTile('15', num_players=1, only_sex='F', sips=1),
    FixmeTile('16'),  # FIXME: Player and first to laugh drinks
    SkipNextTurnTile('17', sips=1),
    NoOpTile('18'),
    EverybodyEffectTile('19', only_sex='F', sips=1),
    RollAgainTile('20', sips=1),
    Tile('21', change_pos_abs=0),
    Tile('22', sips=lambda d: d),
    EverybodyEffectTile('23', has_siblings='B', sips=1),
    FixmeTile('24'),  # FIXME: Choose between drink 3 or go 4 steps back
    Tile('25', sips=1),
    EverybodyEffectTile('26', has_age='even', sips=1),
    EverybodyEffectTile('27', has_age='odd', sips=1),
    NoOpTile('28'),
    Tile('29', sips=5, change_pos_abs=9),
    EverybodyEffectTile('30', max_has_cash=10.00, sips=1),
    FixmeTile('31'),  # FIXME: Roll dice, drink on even, everybody else drink on odd
    Tile('32', sips=3),  # FIXME: Kiss people
    Tile('33', sips=1, lose_clothing=True),
    ChoiceTile('34', num_players=1, change_pos_abs=6),
    Tile('35', change_pos_abs=6),
    FixmeTile('36'),  # FIXME: closest to start drinks and goes there
    FixmeTile('37'),  # FIXME: everybody in front of player drink
    NoOpTile('38'),
    Tile('39', sips=1, lose_clothing=True),
    Tile('40', sips=lambda d: d),
    FixmeTile('41'),  # FIXME: 41 - Player(s) with least coins drink
    FixmeTile('42'),  # FIXME: 42 - Roll the dice, everybody rolling 1 drinks
    EverybodyEffectTile('43', has_siblings='S', sips=1),
    FixmeTile('44'),  # FIXME: 44 - Drink and left neighbor decides who drinks
    Tile('45', sips=1, change_pos_rel=2),
    FixmeTile('46'),  # FIXME: 46 - heads/tails (heads=everybody drinks, tails=you drink)
    Tile('47', sips=2),
    NoOpTile('48'),
    RollAgainTile('49', change_pos_abs=28),
    Tile('50', sips=1, lose_clothing=True),
    Tile('51', sips=3),
    EverybodyEffectTile('52', max_age=20, sips=2),
    NeighborEffectTile('53', sips=1),
    EverybodyEffectTile('54', sips=1),
    FixmeTile('55'),  # FIXME: 55 - everybody rolls; 6=drink
    Tile('56', sips=1, change_pos_abs=18),
    FixmeTile('57'),  # FIXME: 57 - everybody with an 8 in birth year drinks
    NoOpTile('58'),
    FixmeTile('59'),  # FIXME: 59 - everybody rolls; 1=go to start
    SingTile('60', sips=5),  # FIXME
    EverybodyEffectTile('61', has_glasses=False, sips=1),
    FixmeTile('62'),  # FIXME: 62 - Roll and go back num of eyes
    EverybodyEffectTile('63', wears_jeans=True, sips=1),
    EverybodyEffectTile('64', sips=1),
    EverybodyEffectTile('65', change_pos_rel=-1),
    Tile('66', change_pos_abs=32),
    EverybodyEffectTile('67', sips=3, lose_clothing=True),
    NoOpTile('68'),
    FixmeTile('69'),  # FIXME: 69 - roll 5 times and go back num of eyes
    Tile('70', sips=1, change_pos_abs=0),
    WinTile('71'),
]


if __name__ == '__main__':
    max_rounds = 10
    names = [('Fritz', 'M'), ('Pauli', 'F'), ('Hans', 'M'), ('Georg', 'M'), ('Laura', 'F'), ('Sabine', 'F')]

    # Create players
    players = [Player.randomize(name=n[0], sex=n[1]) for n in names]

    for r in range(max_rounds):
        for p in players:
            p.take_turn()
        print("Round finished. Press enter to continue.")
        input()

    print("End of game after {0} rounds".format(max_rounds))
    for p in players:
        print(p)
