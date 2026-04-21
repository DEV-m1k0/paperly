"""
AI support chat endpoint — fully local by default.

Backend is an OpenAI-compatible API; we ship Ollama (http://localhost:11434/v1)
as the default provider so nothing leaves the machine. The daemon and model
are started automatically by our custom `manage.py runserver` — see
`pages/management/commands/ensure_ollama.py`.

POST /api/chat/
  body: { "messages": [{"role": "user"|"assistant", "content": "..."}] }
  response: { "reply": str, "products": [...], "blocked": bool, "reason": str? }
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from django.conf import settings
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from .chat_prompts import PRODUCT_SEARCH_TOOL, build_system_prompt, run_product_search

logger = logging.getLogger(__name__)

MAX_TURNS = 8
MAX_TOOL_ITERATIONS = 4
MAX_USER_MESSAGE_LEN = 1500

PRODUCT_MENTION_RE = re.compile(r"\[product:(\d+)\]")

# Groq's Llama sometimes emits malformed tool calls like
# `<function=search_products>{"query":"..."}</function>` as plain text and
# then Groq rejects the request with code=tool_use_failed. We salvage it
# by regex-extracting the name+JSON from the `failed_generation` field.
_FAILED_TOOL_RE = re.compile(
    r"<function\s*=\s*(?P<name>[\w.-]+)\s*>?\s*(?P<json>\{.*?\})\s*</function>",
    re.DOTALL,
)


def _recover_failed_tool_call(exc) -> list[dict] | None:
    """Return list of {name, arguments} dicts if we can parse the model's
    malformed generation, else None."""
    body = getattr(exc, "body", None) or {}
    if isinstance(body, dict):
        error = body.get("error") or {}
        if error.get("code") != "tool_use_failed":
            return None
        generation = error.get("failed_generation") or ""
    else:
        generation = ""
    if not generation:
        return None
    matches = list(_FAILED_TOOL_RE.finditer(generation))
    if not matches:
        return None
    calls = []
    for m in matches:
        try:
            calls.append({"name": m.group("name"), "arguments": json.loads(m.group("json"))})
        except json.JSONDecodeError:
            continue
    return calls or None


def _rate_limit_check(request) -> tuple[bool, str]:
    limit = getattr(settings, "CHAT_RATE_LIMIT_PER_HOUR", 20)
    now = time.time()
    hour_ago = now - 3600
    history = [t for t in request.session.get("chat_ts", []) if t > hour_ago]
    if len(history) >= limit:
        oldest = min(history)
        wait_min = max(1, int((oldest + 3600 - now) / 60))
        return False, f"Лимит сообщений исчерпан. Попробуйте через {wait_min} мин."
    history.append(now)
    request.session["chat_ts"] = history
    request.session.modified = True
    return True, ""


def _build_messages(raw_messages: list[dict]) -> list[dict]:
    cleaned = []
    for msg in raw_messages[-MAX_TURNS * 2:]:
        role = msg.get("role")
        content = (msg.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        cleaned.append({"role": role, "content": content[:MAX_USER_MESSAGE_LEN]})
    while cleaned and cleaned[-1]["role"] != "user":
        cleaned.pop()
    return cleaned


def _coerce_number(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "да")
    return bool(value)


def _run_tool(name: str, raw_args) -> dict:
    if isinstance(raw_args, dict):
        args = raw_args
    else:
        try:
            args = json.loads(raw_args) if raw_args else {}
        except json.JSONDecodeError:
            return {"error": "invalid tool arguments"}
    if name == "search_products":
        results = run_product_search(
            query=str(args.get("query", "") or "").strip(),
            min_price=_coerce_number(args.get("min_price")),
            max_price=_coerce_number(args.get("max_price")),
            category=(args.get("category") or None),
            brand=(args.get("brand") or None),
            in_stock_only=_coerce_bool(args.get("in_stock_only", False)),
        )
        return {"results": results}
    return {"error": f"unknown tool: {name}"}


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ChatAPIView(View):

    http_method_names = ["post", "options"]

    def post(self, request, *args, **kwargs):
        api_key = getattr(settings, "AI_API_KEY", "") or ""
        api_base = getattr(settings, "AI_API_BASE", "https://api.groq.com/openai/v1")
        model = getattr(settings, "AI_MODEL", "llama-3.3-70b-versatile")

        if not api_key:
            return JsonResponse(
                {
                    "reply": "Чат временно недоступен — AI-ключ не настроен. "
                             "Напишите нам на email или позвоните по телефону из футера сайта.",
                    "blocked": True,
                    "reason": "no_api_key",
                },
                status=503,
            )

        ok, msg = _rate_limit_check(request)
        if not ok:
            return JsonResponse({"reply": msg, "blocked": True, "reason": "rate_limit"}, status=429)

        try:
            body = json.loads(request.body.decode("utf-8")) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        user_messages = _build_messages(body.get("messages") or [])
        if not user_messages:
            return JsonResponse({"error": "No messages provided"}, status=400)

        try:
            from openai import OpenAI, APIError
        except ImportError:
            logger.exception("openai SDK not installed")
            return JsonResponse({"error": "AI client not available"}, status=503)

        client = OpenAI(api_key=api_key, base_url=api_base, timeout=30.0)

        system_prompt = build_system_prompt()
        messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        messages.extend(user_messages)

        tools = [PRODUCT_SEARCH_TOOL]
        mentioned_product_ids: list[int] = []

        for iteration in range(MAX_TOOL_ITERATIONS + 1):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=tools,
                    max_tokens=900,
                    temperature=0.4,
                )
            except APIError as exc:
                # Recover from Llama/GPT-OSS malformed tool calls (Groq code=tool_use_failed).
                recovered = _recover_failed_tool_call(exc)
                if recovered:
                    logger.warning("Recovered %d malformed tool call(s) from Groq", len(recovered))
                    synthetic_tool_calls = []
                    synthetic_results = []
                    for idx, call in enumerate(recovered):
                        call_id = f"salvage_{iteration}_{idx}"
                        result = _run_tool(call["name"], call["arguments"])
                        synthetic_tool_calls.append({
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": call["name"],
                                "arguments": json.dumps(call["arguments"], ensure_ascii=False),
                            },
                        })
                        synthetic_results.append({
                            "role": "tool",
                            "tool_call_id": call_id,
                            "content": json.dumps(result, ensure_ascii=False),
                        })
                    messages.append({
                        "role": "assistant",
                        "content": "",
                        "tool_calls": synthetic_tool_calls,
                    })
                    messages.extend(synthetic_results)
                    continue  # re-ask the model with tool results

                logger.exception("AI provider API error: %s", exc)
                detail = str(exc) if settings.DEBUG else ""
                return JsonResponse(
                    {
                        "reply": (
                            f"Ассистент временно недоступен. {detail}" if detail
                            else "Ассистент временно недоступен. Попробуйте снова через минуту."
                        ),
                        "blocked": True,
                        "reason": "api_error",
                    },
                    status=502,
                )
            except Exception as exc:
                logger.exception("AI client unexpected error: %s", exc)
                detail = f"{type(exc).__name__}: {exc}" if settings.DEBUG else ""
                return JsonResponse(
                    {
                        "reply": f"Ошибка: {detail}" if detail else "Произошла ошибка. Попробуйте чуть позже.",
                        "blocked": True,
                        "reason": "unexpected",
                    },
                    status=502,
                )

            choice = response.choices[0].message
            tool_calls = getattr(choice, "tool_calls", None) or []

            if not tool_calls or iteration >= MAX_TOOL_ITERATIONS:
                final_text = (choice.content or "").strip()
                seen = set()
                for match in PRODUCT_MENTION_RE.finditer(final_text):
                    try:
                        pid = int(match.group(1))
                    except ValueError:
                        continue
                    if pid not in seen:
                        seen.add(pid)
                        mentioned_product_ids.append(pid)

                products_payload = _fetch_products_by_ids(mentioned_product_ids) if mentioned_product_ids else []
                cleaned_reply = PRODUCT_MENTION_RE.sub("", final_text).strip()
                cleaned_reply = re.sub(r"\s{2,}", " ", cleaned_reply)

                return JsonResponse({
                    "reply": cleaned_reply or "Могу подробнее рассказать — что именно интересует?",
                    "products": products_payload,
                    "model": model,
                })

            # Append assistant's tool-call turn, then each tool result.
            messages.append({
                "role": "assistant",
                "content": choice.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            })
            for tc in tool_calls:
                result = _run_tool(tc.function.name, tc.function.arguments)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        return JsonResponse({"reply": "Ассистент не смог ответить."}, status=500)


def _fetch_products_by_ids(ids):
    from shop.models import Product
    products = (
        Product.objects.filter(id__in=ids, status=Product.ProductStatus.ACTIVE)
        .select_related("brand")
        .prefetch_related("images")
    )
    payload = []
    for product in products:
        image = product.images.first()
        image_url = ""
        if image:
            image_url = image.image.url if image.image else (image.image_url or "")
        payload.append({
            "id": product.id,
            "title": product.title,
            "price": float(product.price),
            "old_price": float(product.old_price) if product.old_price else None,
            "image": image_url,
            "brand": product.brand.name if product.brand else "",
            "in_stock": product.stock > 0,
            "url": f"/product/?id={product.id}",
        })
    by_id = {p["id"]: p for p in payload}
    return [by_id[i] for i in ids if i in by_id]
