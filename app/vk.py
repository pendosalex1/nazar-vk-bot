import json
import logging
import os
import re
import secrets
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, VKDemoOrder

logger = logging.getLogger(__name__)

VK_API_VERSION = os.getenv("VK_API_VERSION", "5.199")


def check_vk_request(payload: dict) -> bool:
    expected_secret = os.getenv("VK_CALLBACK_SECRET", "")
    expected_group = os.getenv("VK_GROUP_ID", "")

    if not expected_secret or not expected_group:
        return False

    return (
        str(payload.get("secret", "")) == expected_secret
        and str(payload.get("group_id", "")) == expected_group
    )

TARIFFS = {
    "1": {
        "name": "1 месяц",
        "price": 300,
        "days": 30,
        "devices": 3,
    },
    "3": {
        "name": "3 месяца",
        "price": 700,
        "days": 90,
        "devices": 3,
    },
    "6": {
        "name": "6 месяцев",
        "price": 1000,
        "days": 180,
        "devices": 5,
    },
    "12": {
        "name": "12 месяцев",
        "price": 1500,
        "days": 365,
        "devices": 5,
    },
}


async def request_vk_trial(vk_id: int) -> dict:
    api_url = os.getenv("VK_API_URL", "").rstrip("/")
    api_key = os.getenv("VK_INTERNAL_API_KEY", "")

    if not api_url or not api_key:
        logger.error("VK trial API is not configured")
        return {"error": "unavailable"}

    try:
        async with httpx.AsyncClient(timeout=35) as client:
            response = await client.post(
                f"{api_url}/internal/vk/trial",
                headers={"X-Internal-API-Key": api_key},
                json={"vk_id": vk_id},
            )

        if response.status_code == 409:
            return {"error": "already_activated"}

        response.raise_for_status()
        result = response.json()
        return result if isinstance(result, dict) else {"error": "unavailable"}

    except httpx.HTTPStatusError as exc:
        logger.error("VK trial API returned HTTP %s", exc.response.status_code)
        return {"error": "unavailable"}
    except (httpx.HTTPError, ValueError):
        logger.exception("VK trial API request failed")
        return {"error": "unavailable"}




async def request_vk_subscription(vk_id: int) -> dict:
    api_url = os.getenv("VK_API_URL", "").rstrip("/")
    api_key = os.getenv("VK_INTERNAL_API_KEY", "")

    if not api_url or not api_key:
        logger.error("VK subscription API is not configured")
        return {"error": "unavailable"}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{api_url}/internal/vk/subscription",
                headers={"X-Internal-API-Key": api_key},
                json={"vk_id": vk_id},
            )

        response.raise_for_status()
        result = response.json()
        return result if isinstance(result, dict) else {"error": "unavailable"}

    except httpx.HTTPStatusError as exc:
        logger.error(
            "VK subscription API returned HTTP %s",
            exc.response.status_code,
        )
        return {"error": "unavailable"}
    except (httpx.HTTPError, ValueError):
        logger.exception("VK subscription API request failed")
        return {"error": "unavailable"}


def format_vk_subscription(subscription: dict) -> str:
    active = subscription.get("active") is True

    lines = [
        "Моя подписка",
        "",
        f"Статус: {'Активна' if active else 'Не активна'}",
    ]

    expires_at = subscription.get("expires_at")
    if expires_at:
        try:
            expiry = datetime.fromisoformat(
                str(expires_at).replace("Z", "+00:00")
            )
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            expiry = expiry.astimezone(timezone.utc)
            lines.append(
                f"Действует до: {expiry.strftime('%d.%m.%Y %H:%M UTC')}"
            )
        except (TypeError, ValueError):
            pass

    left_seconds = subscription.get("left_seconds")
    if left_seconds is not None:
        try:
            seconds = max(0, int(float(left_seconds)))
            days, remainder = divmod(seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes = remainder // 60
            lines.append(
                f"Осталось: {days} дн. {hours} ч. {minutes} мин."
            )
        except (TypeError, ValueError):
            pass
    elif subscription.get("left_days") is not None:
        lines.append(f"Осталось дней: {subscription['left_days']}")

    used_gb = subscription.get("traffic_used_gb")
    limit_gb = subscription.get("traffic_limit_gb")

    if used_gb is None and subscription.get("traffic_used_bytes") is not None:
        try:
            used_gb = float(subscription["traffic_used_bytes"]) / (1024 ** 3)
        except (TypeError, ValueError):
            pass

    if limit_gb is None and subscription.get("traffic_limit_bytes") is not None:
        try:
            limit_gb = float(subscription["traffic_limit_bytes"]) / (1024 ** 3)
        except (TypeError, ValueError):
            pass

    if used_gb is not None and limit_gb is not None:
        try:
            lines.append(
                f"Трафик: {float(used_gb):.2f} / {float(limit_gb):.2f} ГБ"
            )
        except (TypeError, ValueError):
            pass
    elif subscription.get("traffic_left_bytes") is not None:
        try:
            remaining_gb = float(subscription["traffic_left_bytes"]) / (1024 ** 3)
            lines.append(f"Остаток трафика: {remaining_gb:.2f} ГБ")
        except (TypeError, ValueError):
            pass

    devices_count = subscription.get("devices_count")
    device_limit = subscription.get("device_limit")

    if devices_count is not None or device_limit is not None:
        lines.append(
            f"Устройства: {devices_count if devices_count is not None else '?'}"
            f" / {device_limit if device_limit is not None else '?'}"
        )

    link = subscription.get("subscription_url")
    if active and isinstance(link, str) and link.startswith(("https://", "vless://")):
        lines.extend(["", "Ссылка подключения:", link])
    elif not active:
        lines.extend(["", "Ссылка подключения недоступна: подписка не активна."])

    return "\n".join(lines)


def main_keyboard() -> dict:
    return {
        "one_time": False,
        "buttons": [
            [
                {
                    "action": {
                        "type": "text",
                        "label": "Тарифы",
                        "payload": json.dumps({"cmd": "tariffs"}),
                    },
                    "color": "primary",
                },
                {
                    "action": {
                        "type": "text",
                        "label": "Моя подписка",
                        "payload": json.dumps({"cmd": "subscription"}),
                    },
                    "color": "secondary",
                },
            ],
            [
                {
                    "action": {
                        "type": "text",
                        "label": "Получить пробный период",
                        "payload": json.dumps({"cmd": "trial"}),
                    },
                    "color": "positive",
                }
            ],
            [
                {
                    "action": {
                        "type": "text",
                        "label": "Помощь",
                        "payload": json.dumps({"cmd": "help"}),
                    },
                    "color": "secondary",
                }
            ],
        ],
    }


def trial_keyboard() -> dict:
    return {
        "one_time": False,
        "buttons": [
            [{
                "action": {
                    "type": "open_link",
                    "label": "Перейти в Telegram",
                    "link": "https://t.me/nazar_vpnbot",
                },
            }],
            [{
                "action": {
                    "type": "text",
                    "label": "Главное меню",
                    "payload": json.dumps({"cmd": "menu"}),
                },
                "color": "secondary",
            }],
        ],
    }


def tariff_keyboard() -> dict:
    buttons = []

    for key, tariff in TARIFFS.items():
        buttons.append([
            {
                "action": {
                    "type": "text",
                    "label": f"{tariff['name']} — {tariff['price']} ₽",
                    "payload": json.dumps(
                        {"cmd": "tariff", "tariff": key},
                    ),
                },
                "color": "primary",
            }
        ])

    buttons.append([
        {
            "action": {
                "type": "text",
                "label": "Главное меню",
                "payload": json.dumps({"cmd": "menu"}),
            },
            "color": "secondary",
        }
    ])

    return {"one_time": False, "buttons": buttons}





def format_demo_orders(orders: list[VKDemoOrder]) -> str:
    if not orders:
        return (
            "У тебя пока нет демонстрационных заказов.\\n"
            "Выбери тариф, чтобы создать тестовый заказ."
        )

    lines = ["Твои демонстрационные заказы:", ""]

    for order in orders:
        tariff = TARIFFS.get(order.tariff_key, {})
        tariff_name = tariff.get("name", order.tariff_key)
        method_names = {
            "crypto": "Крипто (демо)",
            "vk": "VK (демо)",
        }
        status_names = {
            "pending": "Ожидает подтверждения (демо)",
            "cancelled": "Отменён (демо)",
            "completed": "Завершён (демо)",
        }

        lines.extend([
            f"Заказ №{order.id}",
            f"Тариф: {tariff_name}",
            f"Сумма: {order.amount_rub} ₽",
            f"Способ: {method_names.get(order.payment_method, 'Демо')}",
            f"Статус: {status_names.get(order.status, order.status)}",
            "",
        ])

    lines.append("Все записи здесь демонстрационные, без реальных платежей.")
    return "\\n".join(lines)


def demo_orders_keyboard() -> dict:
    return {
        "one_time": False,
        "buttons": [
            [
                {
                    "action": {
                        "type": "text",
                        "label": "Мои демо-заказы",
                        "payload": json.dumps({"cmd": "demo_orders"}),
                    },
                    "color": "primary",
                }
            ],
            [
                {
                    "action": {
                        "type": "text",
                        "label": "К тарифам",
                        "payload": json.dumps({"cmd": "tariffs"}),
                    },
                    "color": "secondary",
                },
                {
                    "action": {
                        "type": "text",
                        "label": "Главное меню",
                        "payload": json.dumps({"cmd": "menu"}),
                    },
                    "color": "secondary",
                },
            ],
        ],
    }


def demo_payment_keyboard(order_id: int) -> dict:
    buttons = [
        [
            {
                "action": {
                    "type": "text",
                    "label": "Крипто (демо)",
                    "payload": json.dumps(
                        {"cmd": "demo_payment", "order": order_id, "method": "crypto"}
                    ),
                },
                "color": "primary",
            }
        ],
        [
            {
                "action": {
                    "type": "text",
                    "label": "VK (демо)",
                    "payload": json.dumps(
                        {"cmd": "demo_payment", "order": order_id, "method": "vk"}
                    ),
                },
                "color": "primary",
            }
        ],
        [
            {
                "action": {
                    "type": "text",
                    "label": "Главное меню",
                    "payload": json.dumps({"cmd": "menu"}),
                },
                "color": "secondary",
            }
        ],
    ]
    return {"one_time": False, "buttons": buttons}


async def send_vk_message(
    peer_id: int,
    message: str,
    keyboard: dict | None = None,
) -> None:
    token = os.getenv("VK_GROUP_TOKEN", "")

    if not token:
        logger.error("VK_GROUP_TOKEN is not configured")
        return

    params = {
        "access_token": token,
        "v": VK_API_VERSION,
        "peer_id": peer_id,
        "random_id": secrets.randbelow(2_000_000_000),
        "message": message,
    }

    if keyboard is not None:
        params["keyboard"] = json.dumps(
            keyboard,
            ensure_ascii=False,
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "https://api.vk.com/method/messages.send",
                data=params,
            )
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                error = result.get("error") or {}
                logger.error(
                    "VK API error: code=%s message=%s",
                    error.get("error_code"),
                    error.get("error_msg"),
                )

    except httpx.HTTPError:
        logger.exception("VK message delivery failed")


def valid_email(value: str) -> bool:
    return bool(
        re.fullmatch(
            r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
            r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
            r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+",
            value,
        )
    )


def get_command(
    message: dict,
    text: str,
) -> tuple[str, str | None, int | None, str | None]:
    payload = message.get("payload")

    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            payload = {}

    if isinstance(payload, dict):
        command = payload.get("cmd")
        tariff = payload.get("tariff")
        order = payload.get("order")
        method = payload.get("method")

        if isinstance(command, str):
            try:
                order_id = int(order) if order is not None else None
            except (TypeError, ValueError):
                order_id = None

            if order_id is not None and order_id <= 0:
                order_id = None

            if not isinstance(method, str):
                method = None

            return (
                command,
                str(tariff) if tariff is not None else None,
                order_id,
                method,
            )

    normalized = text.lower().strip()

    commands = {
        "тарифы": "tariffs",
        "моя подписка": "subscription",
        "подписка": "subscription",
        "получить пробный период": "trial",
        "пробный период": "trial",
        "помощь": "help",
        "главное меню": "menu",
        "меню": "menu",
        "мои демо-заказы": "demo_orders",
    }

    return commands.get(normalized, "unknown"), None, None, None


def tariffs_text() -> str:
    lines = ["Доступные тарифы Nazar:\n"]

    for tariff in TARIFFS.values():
        lines.append(
            f"• {tariff['name']} — {tariff['price']} ₽\n"
            f"  Срок: {tariff['days']} дней\n"
            f"  Трафик: без ограничений\n"
            f"  Устройств: {tariff['devices']}\n"
        )

    lines.append(
        "Выбери тариф кнопкой ниже.\n"
        "Сейчас доступен только просмотр каталога."
    )

    return "\n".join(lines)


async def process_message(
    payload: dict,
    db: Session,
) -> None:
    obj = payload.get("object") or {}
    message = obj.get("message") or obj

    vk_id = message.get("from_id")
    peer_id = message.get("peer_id")
    text = (message.get("text") or "").strip()

    if not isinstance(vk_id, int) or vk_id <= 0:
        return

    if not isinstance(peer_id, int):
        return

    user = db.scalar(
        select(User).where(User.vk_id == vk_id)
    )

    if user is None:
        user = User(vk_id=vk_id)
        db.add(user)
        db.commit()

        await send_vk_message(
            peer_id,
            "Добро пожаловать! Регистрация в Nazar началась.\n\n"
            "Можешь указать email для связи или восстановления доступа. "
            "Email необязателен.\n\n"
            "Если не хочешь указывать email, напиши «Пропустить».",
        )
        return

    if user.status == "awaiting_email":
        if text.lower() in {"пропустить", "пропуск", "skip"}:
            user.email_skipped = True
            user.status = "active"
            db.commit()

            await send_vk_message(
                peer_id,
                "Регистрация завершена! Email пропущен.\n"
                "Позже его можно будет добавить в профиле.",
                main_keyboard(),
            )
            return

        if valid_email(text):
            user.email = text.lower()
            user.status = "active"
            db.commit()

            await send_vk_message(
                peer_id,
                "Email сохранён. Регистрация завершена!",
                main_keyboard(),
            )
            return

        await send_vk_message(
            peer_id,
            "Введи корректный email или напиши «Пропустить».",
        )
        return

    command, tariff_key, order_id, payment_method = get_command(message, text)

    if command == "demo_orders":
        orders = db.scalars(
            select(VKDemoOrder)
            .where(VKDemoOrder.vk_id == vk_id)
            .order_by(VKDemoOrder.id.desc())
            .limit(10)
        ).all()

        await send_vk_message(
            peer_id,
            format_demo_orders(orders),
            demo_orders_keyboard(),
        )
        return

    if command == "menu":
        await send_vk_message(
            peer_id,
            "Главное меню Nazar. Выбери нужный раздел:",
            main_keyboard(),
        )
        return

    if command == "tariffs":
        await send_vk_message(
            peer_id,
            tariffs_text(),
            tariff_keyboard(),
        )
        return

    if command == "tariff":
        tariff = TARIFFS.get(tariff_key or "")

        if tariff is None:
            await send_vk_message(
                peer_id,
                "Не удалось определить тариф. Открой каталог ещё раз.",
                tariff_keyboard(),
            )
            return

        order = VKDemoOrder(
            vk_id=vk_id,
            tariff_key=tariff_key,
            amount_rub=tariff["price"],
            payment_method="not_selected",
            status="pending",
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        await send_vk_message(
            peer_id,
            f"Демонстрационный заказ №{order.id}\n"
            f"Тариф: {tariff['name']}\n"
            f"Стоимость: {tariff['price']} ₽\n"
            f"Срок: {tariff['days']} дней\n"
            f"Трафик: без ограничений\n"
            f"Устройств: {tariff['devices']}\n\n"
            "Выбери демонстрационный способ оплаты.\n"
            "Реальные платежи не выполняются, подписка не активируется.",
            demo_payment_keyboard(order.id),
        )
        return

    if command == "demo_payment":
        if order_id is None or payment_method not in {"crypto", "vk"}:
            await send_vk_message(
                peer_id,
                "Некорректные данные демонстрационного заказа.",
                demo_orders_keyboard(),
            )
            return

        order = db.scalar(
            select(VKDemoOrder).where(
                VKDemoOrder.id == order_id,
                VKDemoOrder.vk_id == vk_id,
            )
        )

        if order is None:
            await send_vk_message(
                peer_id,
                "Демонстрационный заказ не найден.",
                demo_orders_keyboard(),
            )
            return

        if order.status != "pending":
            await send_vk_message(
                peer_id,
                "Этот демонстрационный заказ уже не ожидает подтверждения.",
                demo_orders_keyboard(),
            )
            return

        order.payment_method = payment_method
        db.commit()

        method_name = (
            "Крипто (демо)" if payment_method == "crypto" else "VK (демо)"
        )

        await send_vk_message(
            peer_id,
            f"Для заказа №{order.id} выбран вариант: {method_name}.\n\n"
            "Статус: ожидает подтверждения (демо).\n"
            "Реальные платежи не выполняются. VPN-подписка не активирована.",
            demo_orders_keyboard(),
        )
        return

    if command == "trial":
        result = await request_vk_trial(vk_id)

        if result.get("error") == "already_activated" or result.get("already_activated"):
            link = result.get("subscription_url")
            if result.get("active") and isinstance(link, str) and link.startswith(("https://", "vless://")):
                message_text = (
                    "Пробный период уже был активирован ранее. Повторно получить его нельзя.\n\n"
                    f"Твоя ссылка подключения:\n{link}"
                )
            else:
                message_text = (
                    "Пробный период уже был использован. Повторная активация недоступна."
                )
            keyboard = (
                trial_keyboard()
                if result.get("active") and isinstance(link, str)
                and link.startswith(("https://", "vless://"))
                else main_keyboard()
            )
            await send_vk_message(peer_id, message_text, keyboard)
            return

        link = result.get("subscription_url")
        if result.get("status") != "ok" or not isinstance(link, str) or not link.startswith(("https://", "vless://")):
            await send_vk_message(
                peer_id,
                "Не удалось выдать пробный период. Попробуй немного позже.",
                main_keyboard(),
            )
            return

        await send_vk_message(
            peer_id,
            "Пробный период успешно активирован!\n\n"
            "Срок: 2 дня\n"
            "Трафик: 2 ГБ\n"
            "Устройств: 1\n\n"
            f"Ссылка подключения:\n{link}",
            trial_keyboard(),
        )
        return

    if command == "subscription":
        result = await request_vk_subscription(vk_id)

        if result.get("error") == "unavailable":
            message_text = (
                "Не удалось получить информацию о подписке. "
                "Попробуй немного позже."
            )
        elif result.get("status") == "not_found":
            message_text = (
                "У тебя пока нет подписки.\\n\\n"
                "Можешь получить пробный период или посмотреть тарифы."
            )
        elif (
            result.get("status") == "ok"
            and isinstance(result.get("subscription"), dict)
        ):
            message_text = format_vk_subscription(result["subscription"])
        else:
            message_text = (
                "Не удалось получить информацию о подписке. "
                "Попробуй немного позже."
            )

        await send_vk_message(peer_id, message_text, trial_keyboard())
        return

    if command == "help":
        await send_vk_message(
            peer_id,
            "Помощь Nazar\n\n"
            "Здесь ты можешь управлять своим подключением и узнать больше о возможностях бота.\n\n"
            "Доступные команды:\n"
            "Получить пробный период — запросить бесплатный пробный доступ.\n"
            "Тарифы — посмотреть доступные варианты подписки.\n"
            "Моя подписка — проверить статус подключения и параметры подписки.\n"
            "Мои демо-заказы — посмотреть историю созданных заказов.\n\n"
            "Важно: оформление заказов и выбор способа оплаты сейчас работают только в демонстрационном режиме. "
            "Реальные платежи не принимаются, платные подписки автоматически не активируются.\n\n"
            "Остались вопросы? Напиши их следующим сообщением — постараемся разобраться.",
            main_keyboard(),
        )
        return

    await send_vk_message(
        peer_id,
        "Ты уже зарегистрирован в Nazar!\n"
        "Выбери раздел в меню ниже.",
        main_keyboard(),
    )
