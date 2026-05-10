package com.example.sandbox.store;

import com.example.sandbox.arcade.ScoreValue;

public class ScoreRepository {
    public ScoreValue loadCurrentScore(String playerId) {
        return new ScoreValue(0);
    }
}
