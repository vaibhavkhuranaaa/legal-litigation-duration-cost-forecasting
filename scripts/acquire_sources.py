from litigation_planner.acquisition import AcquisitionError, main

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AcquisitionError as error:
        raise SystemExit(f"source acquisition failed: {error}") from error
