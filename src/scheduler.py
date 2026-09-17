from datetime import datetime


def should_execute_check():
    now = datetime.now()
    # Karácsonyi időszak: Dec 15 - Jan 5 (minden nap aktív)
    is_holiday_mode = (now.month == 12 and now.day >= 15) or (now.month == 1 and now.day <= 5)

    # Heti időszak: Csütörtök (weekday == 3) 17:00 után
    is_thursday_drop = (now.weekday() == 3 and now.hour >= 17)

    return is_holiday_mode or is_thursday_drop