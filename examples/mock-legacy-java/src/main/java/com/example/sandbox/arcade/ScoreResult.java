package com.example.sandbox.arcade;

public class ScoreResult {
    private final String playerId;
    private final ScoreValue finalScore;

    public ScoreResult(String playerId, ScoreValue finalScore) {
        this.playerId = playerId;
        this.finalScore = finalScore;
    }

    public String getPlayerId() {
        return playerId;
    }

    public ScoreValue getFinalScore() {
        return finalScore;
    }
}
