from src.tests.harness.determinism_harness import DeterminismTestHarness


def main():
    print("Initializing Determinism Test Harness (FIXED)...")
    harness = DeterminismTestHarness()

    try:
        print("1. Running Simulation (Live)...")
        # Run enough ticks to trigger events, budget changes, and snapshots
        # We need enough ticks for the MockAdapter to fire and feedback to loop back
        live_state = harness.run_simulation(ticks=20)
        print("   Live simulation complete.")

        print("2. Running Replay (Restart)...")
        # This creates a fresh orchestrator that loads from disk/ledger
        replay_state = harness.run_replay()
        print("   Replay complete.")

        print("3. Comparing States...")
        if harness.compare_states(live_state, replay_state):
            print("\nCORE STRATEGIC SYSTEM SANITY CHECK: PASSED")
            print(f"Final Mode: {live_state['snapshot'].mode}")
            print(f"Final Budget Energy: {live_state['budget'].energy_budget:.2f}")
        else:
            print("\nFAILURE: State mismatch detected.")
            exit(1)

    except Exception as e:
        print(f"\nCRITICAL FAILURE: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    finally:
        harness.cleanup()


if __name__ == "__main__":
    main()