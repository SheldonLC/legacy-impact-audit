package com.example.sandbox.job;

import java.util.List;

public class LegacyJobRunner {
    private final List<LegacyJob> jobs;

    public LegacyJobRunner(List<LegacyJob> jobs) {
        this.jobs = jobs;
    }

    public void execute() {
        for (LegacyJob job : jobs) {
            job.execute();
        }
    }
}
