from src.tests.harness.invariant_test_harness import InvariantTestHarness


def main():
    print("Running Invariant Tests (Stage F.2)...")
    harness = InvariantTestHarness()

    try:
        harness.test_budget_rollback_on_failure()

        # Re-init for next test to clear state
        harness.cleanup()
        harness = InvariantTestHarness()

        harness.test_replay_poisoning()

        print("\nALL INVARIANT TESTS PASSED")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
    finally:
        harness.cleanup()


if __name__ == "__main__":
    main()