STREAK_BONUS_THRESHOLD = 3
players = {
    "a": 3,
    "b": 1,
    "c": 5,
    "d": 5,
    "e": 7

}
players = {
    "a": 3,
    "b": 1
}
QUIZ_MASTER = 'aaa'
SKIP_QUIZ_MASTER_IN_RESULTS = True


def find_high_streak_players():
    all_streaks = []
    for user_id, streak in players.items():
        if user_id == QUIZ_MASTER and SKIP_QUIZ_MASTER_IN_RESULTS:
            pass
        else:
            if streak >= STREAK_BONUS_THRESHOLD:
                all_streaks.append(
                    (streak, user_id))
    if not all_streaks:
        return None  # Nobody got a streak over the threshold

    all_streaks.sort(reverse=True)
    print(all_streaks)
    highest_streakers = []
    if len(all_streaks) == 1:
        highest_streakers = all_streaks.copy()
        return highest_streakers

    first_item = all_streaks.pop(0)
    highest_streakers.append(first_item)
    next_item_lower = False
    while not next_item_lower:
        next_item = all_streaks.pop(0)
        # Compare streak count
        if next_item[0] == first_item[0]:
            highest_streakers.append(next_item)
        else:
            next_item_lower = True

    return highest_streakers


print(find_high_streak_players())
