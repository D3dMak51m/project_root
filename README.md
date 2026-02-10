# AIHuman Project

Platform-independent system of autonomous AI-HUMANS.

## Stage 9.F Invariants (STRICT)

1. **No Reactivity**: The system never reacts directly to external events.
2. **No Automatic Responses**: Messages do not trigger replies.
3. **Silence is Default**: Inaction is the preferred state.
4. **LifeLoop is the Only Mutator**: All state changes happen exclusively within the LifeLoop tick.

> **WARNING**: Any logic outside LifeLoop is an architectural error.