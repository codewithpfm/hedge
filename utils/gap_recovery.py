def recover_weekend_gaps(df, data, logger):
    """
    Recover orphaned 8M signal bars whose timestamp doesn't exist in the 1M HF index.
    Snaps exits onto the next existing 1M bar (skipping Sunday bars).
    """
    orphan_mask = ~df.index.isin(data.index)
    if not orphan_mask.any():
        return data

    orphan_df = df[orphan_mask]
    non_sunday_idx = data.index[data.index.dayofweek != 6]
    n_rescued = 0
    n_dropped_entries = 0

    for orphan_ts in orphan_df.index:
        for side in ("long", "short"):
            if orphan_df.at[orphan_ts, f"{side}_entries"]:
                n_dropped_entries += 1
                logger.warning(
                    f"[ORPHAN ENTRY DROPPED] {side.upper()} @ {orphan_ts} | "
                    f"no matching 1M bar in HF data"
                )

            if not orphan_df.at[orphan_ts, f"{side}_exits"]:
                continue

            pos = non_sunday_idx.searchsorted(orphan_ts, side="left")
            if pos >= len(non_sunday_idx):
                logger.warning(
                    f"[ORPHAN EXIT DROPPED] {side.upper()} @ {orphan_ts} | "
                    f"no Mon-Fri 1M bar after orphan"
                )
                continue

            target_ts = non_sunday_idx[pos]
            prefix = f"sigs_{side}"
            original_reason = orphan_df.at[orphan_ts, f"{prefix}_exit_reason"]
            target_open = float(data.at[target_ts, "Open"])

            if bool(data.at[target_ts, f"{side}_exits"]):
                logger.warning(
                    f"[GAP RESCUE COLLISION] {target_ts} already has "
                    f"{side}_exits=True; overwriting with weekend_gap_recovery "
                    f"from orphan {orphan_ts}"
                )

            data.at[target_ts, f"{side}_exits"] = True
            data.at[target_ts, f"{prefix}_exit_reason"] = "weekend_gap_recovery"
            data.at[target_ts, f"{prefix}_exit_price"] = target_open

            gap_hours = (target_ts - orphan_ts).total_seconds() / 3600
            logger.warning(
                f"[GAP RESCUE] {side.upper()} | "
                f"orphan={orphan_ts} -> target={target_ts} | "
                f"gap={gap_hours:.1f}h | "
                f"reason={original_reason} -> weekend_gap_recovery | "
                f"exit_open={target_open:.5f}"
            )
            n_rescued += 1

    logger.warning(
        f"weekend_gap_recovery summary: rescued {n_rescued} exits, "
        f"dropped {n_dropped_entries} entries from {orphan_mask.sum()} orphan 8M bars"
    )
    return data
