from datetime import datetime

# Nyilvántartja a legutolsó sikeres háttérvizsgálat idejét
LAST_CHECK_TIME = None


def is_claim_time_now():
    global LAST_CHECK_TIME
    now = datetime.now()
    LAST_CHECK_TIME = now

    # Karácsonyi napi ciklus (dec. 15 - jan. 5)
    is_xmas = (now.month == 12 and now.day >= 15) or (now.month == 1 and now.day <= 5)
    # Csütörtök 17:00 utáni heti ciklus (3 = csütörtök)
    is_thursday_evening = (now.weekday() == 3 and now.hour >= 17)

    return is_xmas or is_thursday_evening


should_execute_check = is_claim_time_now