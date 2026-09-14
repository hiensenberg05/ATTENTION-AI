# Phase 1D — Candidate Signal Coverage Diagnosis

Dataset A only; this is diagnosis, not a revised candidate generator.

## Finding

Phase 1C omitted the broad `interaction_change` signal (adjacent event types differ). It covers 97.5% of GT boundaries, versus 37.6% for the existing combined candidate set, but fires on 65.5% of all transitions (106,637 candidates). It therefore explains most misses but is not usable alone.

Temporal gap and density change each cover about 37%; browser activity covers 27.6%; app/window changes cover about 2%; clipboard at the exact transition covers none. The missed boundaries are therefore primarily immediate, same-context transitions whose event type often changes, rather than breaks marked by idle time or app switching.

## What information is missing?

The current generator lacks a sequence-sensitive change representation: event-type change is high recall but too broad. Future work should test compact multi-event sequence change or candidate consolidation around local bursts, aiming to reduce the high-density interaction-change set before any ranking. It should not add app changes, chunks, or clipboard as direct rules.
