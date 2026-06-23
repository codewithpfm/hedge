def TF_TO_MINUTES(tf: str) -> int:
    """Convert a timeframe string like '4H', '1D', '2H' to total minutes."""
    if not tf:
        raise ValueError("Timeframe string required")
    match tf:
        case "1M":  return 1
        case "2M":  return 2
        case "5M":  return 5
        case "8M":  return 8
        case "15M": return 15
        case "30M": return 30
        case "45M": return 45
        case "1H":  return 60
        case "2H":  return 120
        case "3H":  return 180
        case "4H":  return 240
        case "6H":  return 360
        case "8H":  return 480
        case "12H": return 720
        case "1D":  return 1440
        case "1W":  return 10080
    raise ValueError(f"Unsupported timeframe: {tf}")


def TF_TO_HOURS(tf: str) -> int:
    """Convert a timeframe string to whole hours (must be >= 1H)."""
    m = TF_TO_MINUTES(tf)
    if m < 60 or m % 60 != 0:
        raise ValueError(f"TF_TO_HOURS requires a whole-hour timeframe, got {tf}")
    return m // 60


def TF_CRON_HOURS(tf: str) -> str:
    """Return APScheduler cron `hour` string for a given HTF.
    E.g. '4H' → '0,4,8,12,16,20', '2H' → '0,2,4,...,22', '1D' → '0'.
    """
    minutes = TF_TO_MINUTES(tf)
    if minutes < 60:
        raise ValueError(f"TF_CRON_HOURS requires >= 1H timeframe, got {tf}")
    hours = minutes // 60
    if hours >= 24:
        return "0"
    return ",".join(str(h) for h in range(0, 24, hours))


def POLYGON_TF(tf):
    
    if not tf:
        raise Exception("Please provide timeframe: 1M, 2M, 5M, 15M, 30M, 1H, 4H, 1D, 1W, 1Y")
    
    match tf:
        case "1M": 
            return "1 minute"
        case "2M": 
            return "2 minutes"
        case "5M":
            return "5 minutes"
        case "15M":
            return "15 minutes"
        case "30M":
            return "30 minutes"
        case "1H":
            return "1 hour"
        case "4H":
            return "4 hours"
        case "1D":
            return "1 day"
        case  "1W":
            return "1 week"
        case  "1Y":
            return "1 year"

    raise ValueError("Invalid time frame")


def RESAMPLE_TF(tf):

    if not tf:
        raise Exception("Please provide timeframe: 1M, 2M, 5M, 15M, 30M, 1H, 4H, 1D, 1W, 1Y")

    match tf:
        case  "1M":
            return "1 Min"
        case  "2M":
            return "2 Min"
        case  "5M":
            return "5 Min"
        case  "8M":
            return "8 Min"
        case  "15M":
            return "15 Min"
        case  "30M":
            return "30 Min"
        case  "1H":
            return "1h"
        case "2H":
            return "2h"
        case "3H":
            return "3h"
        case  "4H":
            return "4h"
        case "6H":
            return "6h"
        case "8H":
            return "8h"
        case "12H":
            return "12h"
        case  "1D":
            return "D"
        case  "1W":
            return "W"
        case  "1Y":
            return "Y"

    return tf + " Min"


def CHECK_TF(tf):
    
    if not tf:
        raise Exception("Please provide timeframe: 1M, 2M, 5M, 15M, 30M, 1H, 4H, 1D, 1W, 1Y")
    
    match tf:
        case "1M":
            raise Exception("1 minute timeframe is not supported")
        case "2M":
            raise Exception("2 minute timeframe is not supported")
        case "5M":
            return 3
        case "8M":
            return 5
        case "15M":
            return 12
        case "30M":
            return 24
        case "45M":
            return 35
        case "1H":
            return 45
        case "2H":
            return 90
        case "3H":
            return 150
        case "4H":
            return 210
        case "1D":
            return 1200
        case "1W":
            return 9999
        case "1Y":
            return 520000