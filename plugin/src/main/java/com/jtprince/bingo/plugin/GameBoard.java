package com.jtprince.bingo.plugin;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

public class GameBoard {
    final BingoGame game;

    protected boolean filled = false;
    protected final ConcreteGoal[] squares = new ConcreteGoal[25];

    public GameBoard(BingoGame game) {
        this.game = game;
    }

    public void setSquares(ConcreteGoal[] squares) {
        if (squares.length != this.squares.length) {
            throw new ArrayIndexOutOfBoundsException("setSquares must be called with 25 Goals");
        }
        System.arraycopy(squares, 0, this.squares, 0, 25);
        this.filled = true;

        Set<ConcreteGoal> autoActivatedGoals =
            this.game.autoActivation.listener.registerGoals(Arrays.asList(squares));

        this.game.plugin.getLogger().info("Auto activation on:" + String.join(", ",
            autoActivatedGoals.stream().map(cg -> cg.id).collect(Collectors.toUnmodifiableList())));
    }

    public List<ConcreteGoal> getSquares() {
        if (!this.filled) {
            return Collections.emptyList();
        }

        return Arrays.asList(squares);
    }

    public ConcreteGoal getSquare(int position) {
        return this.squares[position];
    }
}
