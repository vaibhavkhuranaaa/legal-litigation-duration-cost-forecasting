from litigation_planner.raw_platform import RawPlatformError, main

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RawPlatformError as error:
        raise SystemExit(f"raw platform failed: {error}") from error
