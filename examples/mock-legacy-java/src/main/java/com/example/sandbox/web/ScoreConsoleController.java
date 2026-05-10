package com.example.sandbox.web;

import com.example.sandbox.arcade.ArcadeScoreService;
import com.example.sandbox.arcade.PlayerProfile;
import com.example.sandbox.arcade.ScoreDelta;
import com.example.sandbox.arcade.ScoreResult;

public class ScoreConsoleController {
    private final ArcadeScoreService service;

    public ScoreConsoleController(ArcadeScoreService service) {
        this.service = service;
    }

    public ScoreResult approveManualScoreChange(String playerId, ScoreDelta delta) {
        PlayerProfile player = new PlayerProfile(playerId, "GOLD");
        return service.recomputePlayerScore(player, delta);
    }
}
