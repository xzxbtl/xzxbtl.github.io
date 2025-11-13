formatted_dict = {
    0: "Пользователь",
    1: "Подписчик 1-ого уровня",
    2: "Подписчик 2-ого уровня",
    3: "Подписчик 3-его уровня"
}


def formatted_status(admin: bool, subscribe_lvl: int):
    if admin:
        return "Админ"
    else:
        return formatted_dict[subscribe_lvl]


def formatted_time_sub(subscription_expires):
    if not subscription_expires:
        return "`Отсуствует`"

    formatted = subscription_expires.strftime("%d.%m.%Y %H:%M")
    return f"*До:* `{formatted}`"

