package com.example.sandbox.job;

import com.example.sandbox.arcade.ArcadeScoreService;
import com.example.sandbox.arcade.PlayerProfile;
import com.example.sandbox.arcade.ScoreDelta;
import com.example.sandbox.arcade.ScoreResult;

public class TournamentJob implements LegacyJob {
    private final ArcadeScoreService arcadeScoreService;

    public TournamentJob(ArcadeScoreService arcadeScoreService) {
        this.arcadeScoreService = arcadeScoreService;
    }

    @Override
    public void execute() {
        PlayerProfile player = new PlayerProfile("PLAYER-100", "GOLD");
        ScoreResult result = arcadeScoreService.recomputePlayerScore(player, new ScoreDelta(10));
        publish(result);
    }

    private void publish(ScoreResult result) {
        // Publish to downstream scoreboard queue.
    }
}
