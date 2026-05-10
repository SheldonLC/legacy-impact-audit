package com.example.sandbox.arcade;

public class ScoreDelta {
    private final int points;

    public ScoreDelta(int points) {
        this.points = points;
    }

    public ScoreValue asScoreValue() {
        return new ScoreValue(points);
    }
}
