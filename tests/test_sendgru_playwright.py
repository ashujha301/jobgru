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
    _leftmost_visible_locator,
    already_connected_or_pending,
    check_stop,
    click_connect,
    header_connect_locator,
    header_follow_visible,
    header_more_locator,
    is_first_degree_connected,
    is_pending,
    load_actionable_rows,
    message_button_locator,
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


class ProfileActionScopeTests(unittest.TestCase):
    def test_leftmost_skips_sidebar_x(self):
        root = MagicMock()
        sidebar = MagicMock()
        sidebar.is_visible.return_value = True
        sidebar.bounding_box.return_value = {"x": 965, "y": 531, "width": 58, "height": 32}
        header = MagicMock()
        header.is_visible.return_value = True
        header.bounding_box.return_value = {"x": 300, "y": 531, "width": 58, "height": 32}
        root.count.return_value = 2
        root.nth.side_effect = lambda i: header if i == 0 else sidebar

        picked = _leftmost_visible_locator(root, y_anchor=531)
        self.assertIs(picked, header)

    def test_header_more_uses_profile_action_scope(self):
        page = MagicMock()
        more_btn = MagicMock()
        with unittest.mock.patch(
            "sendgru_playwright._leftmost_visible_locator", return_value=more_btn
        ) as pick, unittest.mock.patch(
            "sendgru_playwright._profile_action_y_anchor", return_value=531.0
        ):
            result = header_more_locator(page)
        self.assertIs(result, more_btn)
        pick.assert_called_once()
        args, kwargs = pick.call_args
        self.assertEqual(kwargs.get("y_anchor"), 531.0)


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
        with unittest.mock.patch("sendgru_playwright.header_connect_locator", return_value=MagicMock()), unittest.mock.patch(
            "sendgru_playwright.header_follow_visible", return_value=False
        ), unittest.mock.patch("sendgru_playwright.header_more_locator", return_value=None), unittest.mock.patch(
            "sendgru_playwright.message_button_locator", return_value=None
        ), unittest.mock.patch("sendgru_playwright.is_pending", return_value=False):
            self.assertFalse(is_first_degree_connected(page))
            self.assertFalse(already_connected_or_pending(page))

    def test_follow_and_more_not_skipped(self):
        page = MagicMock()
        page.inner_text.return_value = ""
        with unittest.mock.patch("sendgru_playwright.header_connect_locator", return_value=None), unittest.mock.patch(
            "sendgru_playwright.header_follow_visible", return_value=True
        ), unittest.mock.patch("sendgru_playwright.header_more_locator", return_value=MagicMock()), unittest.mock.patch(
            "sendgru_playwright.is_pending", return_value=False
        ):
            self.assertFalse(is_first_degree_connected(page))

    def test_message_only_is_connected_not_pending_skip(self):
        page = MagicMock()
        page.inner_text.return_value = ""
        with unittest.mock.patch("sendgru_playwright.header_connect_locator", return_value=None), unittest.mock.patch(
            "sendgru_playwright.header_follow_visible", return_value=False
        ), unittest.mock.patch("sendgru_playwright.header_more_locator", return_value=None), unittest.mock.patch(
            "sendgru_playwright.message_button_locator", return_value=MagicMock()
        ), unittest.mock.patch("sendgru_playwright.is_pending", return_value=False):
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
        with unittest.mock.patch("sendgru_playwright.header_connect_locator", return_value=connect), unittest.mock.patch(
            "sendgru_playwright._safe_click", return_value=True
        ) as click:
            self.assertTrue(click_connect(page))
        click.assert_called_with(connect)

    def test_follow_uses_more_menu(self):
        page = MagicMock()
        more = MagicMock()
        menu_connect = MagicMock()
        with unittest.mock.patch("sendgru_playwright.header_connect_locator", return_value=None), unittest.mock.patch(
            "sendgru_playwright.header_follow_visible", return_value=True
        ), unittest.mock.patch("sendgru_playwright.header_more_locator", return_value=more), unittest.mock.patch(
            "sendgru_playwright.dropdown_connect_locator", return_value=menu_connect
        ), unittest.mock.patch("sendgru_playwright._safe_click", side_effect=[True, True]) as click:
            self.assertTrue(click_connect(page))
        self.assertEqual(click.call_args_list[0][0][0], more)
        self.assertEqual(click.call_args_list[1][0][0], menu_connect)


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
