package com.example.sandbox.arcade;

public class ScoreValue {
    private final int value;

    public ScoreValue(int value) {
        this.value = value;
    }

    public ScoreValue plus(ScoreValue other) {
        return new ScoreValue(value + other.value);
    }
}
