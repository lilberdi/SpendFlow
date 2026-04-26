# -*- coding: utf-8 -*-
"""Дымовые тесты диалоговой логики process_text_message."""

import networkx as nx

import logic


def test_process_text_message_none():
    assert "не понял" in logic.process_text_message(None, None).lower()


def test_process_text_message_greeting():
    out = logic.process_text_message("Привет!", nx.Graph())
    assert "spendflow" in out.lower() or "учет" in out.lower()


def test_process_text_message_finds_node_in_graph():
    g = nx.Graph()
    g.add_edge("Uber", "Transport")
    out = logic.process_text_message("uber", g)
    assert "uber" in out.lower()
    assert "граф" in out.lower()
