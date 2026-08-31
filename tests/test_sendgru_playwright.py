#!/usr/bin/env python3
"""Unit tests for SendGru Playwright fallback helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from sendgru_playwright import (  # noqa: E402
    already_connected_or_pending,
    check_stop,
    click_connect,
    header_connect_locator,
    header_follow_visible,
    is_first_degree_connected,
    is_pending,
    load_actionable_rows,
    send_direct_message,
)


class StopPhraseTests(unittest.TestCase):
    def test_detects_weekly_limit(self):
        page = MagicMock()
        page.inner_text.return_value = "You have reached the weekly invitation limit"
        self.assertEqual(check_stop(page), "weekly invitation limit")

    def test_no_stop_on_normal_page(self):
        page = MagicMock()
        page.inner_text.return_value = "Connect Message More"
        self.assertIsNone(check_stop(page))


class ConnectedTests(unittest.TestCase):
    def test_pending_without_connect(self):
        page = MagicMock()
        page.inner_text.return_value = "pending invitation"
        page.get_by_role.return_value.count.return_value = 0
        page.locator.return_value.count.return_value = 0
        self.assertTrue(is_pending(page))
        self.assertTrue(already_connected_or_pending(page))

    def test_connect_in_header_not_skipped(self):
        page = MagicMock()
        page.inner_text.return_value = ""

        def role_side_effect(role, name=None, **kwargs):
            m = MagicMock()
            pat = getattr(name, "pattern", "") if name else ""
            if role == "button" and pat == "^Connect$":
                m.count.return_value = 1
                m.first.is_visible.return_value = True
            else:
                m.count.return_value = 0
            return m

        page.get_by_role.side_effect = role_side_effect
        page.locator.return_value.count.return_value = 0
        self.assertFalse(is_first_degree_connected(page))
        self.assertFalse(already_connected_or_pending(page))

    def test_follow_and_more_not_skipped(self):
        page = MagicMock()
        page.inner_text.return_value = ""

        def role_side_effect(role, name=None, **kwargs):
            m = MagicMock()
            if role == "button" and name and getattr(name, "pattern", "") == "^Follow$":
                m.count.return_value = 1
                m.first.is_visible.return_value = True
            elif role == "button" and name and getattr(name, "pattern", "") == "^More\\b":
                m.count.return_value = 1
                m.first.is_visible.return_value = True
            else:
                m.count.return_value = 0
            return m

        page.get_by_role.side_effect = role_side_effect
        page.locator.return_value.count.return_value = 0
        self.assertFalse(is_first_degree_connected(page))

    def test_message_only_is_connected_not_pending_skip(self):
        page = MagicMock()
        page.inner_text.return_value = ""

        def role_side_effect(role, name=None, **kwargs):
            m = MagicMock()
            pat = getattr(name, "pattern", "") if name else ""
            if role == "button" and pat == "^Message$":
                m.count.return_value = 1
                m.first.is_visible.return_value = True
            else:
                m.count.return_value = 0
            return m

        page.get_by_role.side_effect = role_side_effect
        page.locator.return_value.count.return_value = 0
        self.assertTrue(is_first_degree_connected(page))
        self.assertTrue(already_connected_or_pending(page))


class DirectMessageTests(unittest.TestCase):
    def test_send_direct_message_success(self):
        page = MagicMock()
        msg_btn = MagicMock()
        msg_btn.click.return_value = None
        compose = MagicMock()
        textbox = MagicMock()
        textbox.count.return_value = 1
        textbox.is_visible.return_value = True
        textbox.input_value.return_value = "Hi, note text"
        compose.locator.return_value.first = textbox
        compose.get_by_role.return_value.first.count.return_value = 1
        compose.get_by_role.return_value.first.is_visible.return_value = True
        compose.inner_text.return_value = "Write a message Send"

        with unittest.mock.patch("sendgru_playwright.message_button_locator", return_value=msg_btn), unittest.mock.patch(
            "sendgru_playwright.wait_for_message_compose", return_value=compose
        ), unittest.mock.patch("sendgru_playwright.fill_message", return_value=True), unittest.mock.patch(
            "sendgru_playwright.click_message_send", return_value=True
        ), unittest.mock.patch("sendgru_playwright.check_stop", return_value=None):
            status, detail = send_direct_message(page, "Hi, note text")
        self.assertEqual(status, "sent")
        self.assertIn("direct message", detail)


class ConnectClickTests(unittest.TestCase):
    def test_header_connect_clicked(self):
        page = MagicMock()
        connect = MagicMock()
        connect.count.return_value = 1
        connect.first.is_visible.return_value = True
        connect.first.click.return_value = None

        def role_side_effect(role, name=None, **kwargs):
            m = MagicMock()
            if role == "button" and name and getattr(name, "pattern", "") == "^Connect$":
                return connect
            m.count.return_value = 0
            return m

        page.get_by_role.side_effect = role_side_effect
        page.locator.return_value.count.return_value = 0
        self.assertTrue(click_connect(page))
        connect.first.click.assert_called()

    def test_follow_uses_more_menu(self):
        page = MagicMock()
        follow = MagicMock()
        follow.count.return_value = 1
        follow.first.is_visible.return_value = True
        more = MagicMock()
        more.count.return_value = 1
        more.first.is_visible.return_value = True
        more.first.click.return_value = None
        menu_connect = MagicMock()
        menu_connect.count.return_value = 1
        menu_connect.first.is_visible.return_value = True
        menu_connect.first.click.return_value = None

        call_idx = {"n": 0}

        def role_side_effect(role, name=None, **kwargs):
            m = MagicMock()
            pat = getattr(name, "pattern", "") if name else ""
            if role == "button" and pat == "^Connect$":
                call_idx["n"] += 1
                return menu_connect if call_idx["n"] > 1 else MagicMock(count=MagicMock(return_value=0))
            if role == "button" and pat == "^Follow$":
                return follow
            if role == "button" and pat == "^More\\b":
                return more
            m.count.return_value = 0
            return m

        page.get_by_role.side_effect = role_side_effect
        page.locator.return_value.count.return_value = 0
        self.assertTrue(click_connect(page))
        more.first.click.assert_called()
        menu_connect.first.click.assert_called()


class SendFlowFallbackTests(unittest.TestCase):
    def test_invite_modal_failure_falls_back_to_message(self):
        page = MagicMock()
        with unittest.mock.patch(
            "sendgru_playwright.send_direct_message", return_value=("sent", "ok (direct message)")
        ) as dm, unittest.mock.patch("sendgru_playwright.message_button_locator", return_value=MagicMock()), unittest.mock.patch(
            "sendgru_playwright.wait_for_invite_modal", return_value=None
        ), unittest.mock.patch("sendgru_playwright.click_connect", return_value=True), unittest.mock.patch(
            "sendgru_playwright.is_pending", return_value=False
        ), unittest.mock.patch(
            "sendgru_playwright.is_first_degree_connected", return_value=False
        ), unittest.mock.patch(
            "sendgru_playwright.check_stop", return_value=None
        ):
            from sendgru_playwright import send_to_person

            status, detail = send_to_person(
                page,
                url="https://www.linkedin.com/in/example/",
                note="Hi there",
                company="Acme",
                first_navigate=True,
            )
        dm.assert_called_once()
        self.assertEqual(status, "sent")
        self.assertEqual(detail, "ok (direct message)")


class LoadRowsTests(unittest.TestCase):
    def test_parse_empty_spec(self):
        actionable, skipped, nums = load_actionable_rows("", apply_daily_cap=False)
        self.assertEqual(nums, [])
        self.assertEqual(actionable, [])


if __name__ == "__main__":
    unittest.main()
