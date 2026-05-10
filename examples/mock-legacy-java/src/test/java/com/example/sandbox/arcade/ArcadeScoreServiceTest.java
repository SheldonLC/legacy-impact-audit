package com.example.sandbox.arcade;

public class ArcadeScoreServiceTest {
    public void shouldRecomputePlayerScore() {
        ArcadeScoreService service = new ArcadeScoreService(null, null, null);
        service.recomputePlayerScore(null, null);
    }
}
