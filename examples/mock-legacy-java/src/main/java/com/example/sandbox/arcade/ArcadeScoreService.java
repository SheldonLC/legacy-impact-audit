package com.example.sandbox.arcade;

import com.example.sandbox.store.ScoreRepository;

public class ArcadeScoreService {
    private final ScoreRepository scoreRepository;
    private final BonusPolicyService bonusPolicyService;
    private final ScoreAuditTrail auditTrail;

    public ArcadeScoreService(
            ScoreRepository scoreRepository,
            BonusPolicyService bonusPolicyService,
            ScoreAuditTrail auditTrail) {
        this.scoreRepository = scoreRepository;
        this.bonusPolicyService = bonusPolicyService;
        this.auditTrail = auditTrail;
    }

    public ScoreResult recomputePlayerScore(PlayerProfile player, ScoreDelta delta) {
        ScoreValue currentScore = scoreRepository.loadCurrentScore(player.getPlayerId());
        ScoreValue bonus = bonusPolicyService.calculateBonus(delta, player.getTierCode());
        ScoreValue finalScore = currentScore.plus(delta.asScoreValue()).plus(bonus);
        auditTrail.recordScoreChange(player.getPlayerId(), delta, finalScore);
        return new ScoreResult(player.getPlayerId(), finalScore);
    }

    public void execute() {
        // Deliberately generic method name for gate testing.
    }
}
