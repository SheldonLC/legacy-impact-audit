package com.example.sandbox.arcade;

public class PlayerProfile {
    private final String playerId;
    private final String tierCode;

    public PlayerProfile(String playerId, String tierCode) {
        this.playerId = playerId;
        this.tierCode = tierCode;
    }

    public String getPlayerId() {
        return playerId;
    }

    public String getTierCode() {
        return tierCode;
    }
}
