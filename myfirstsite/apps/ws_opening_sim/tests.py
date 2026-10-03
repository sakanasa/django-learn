from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

FAKE_DECK = {
    'series_name': 'Test Series',
    'deck_code': 'ABCD',
    'cards': [
        {'card_number': 'T/W01-001', 'card_name': 'A', 'count': 4, 'level': '0',
         'card_type': 'キャラ', 'img': 't/t_w01/t_w01_001.png'},
        {'card_number': 'T/W01-002', 'card_name': 'CX', 'count': 8, 'level': 'CX',
         'card_type': 'クライマックス', 'img': ''},
    ],
}


class OpeningSimTests(TestCase):
    def test_index_renders(self):
        resp = self.client.get(reverse('ws_opening_sim:index'))
        self.assertEqual(resp.status_code, 200)

    def test_load_deck_requires_code(self):
        resp = self.client.post(reverse('ws_opening_sim:load_deck'), {'deck_code': ''})
        self.assertEqual(resp.status_code, 400)

    @patch('apps.ws_opening_sim.views.scrape_deck', return_value=FAKE_DECK)
    def test_load_deck_returns_cards(self, _):
        resp = self.client.post(reverse('ws_opening_sim:load_deck'), {'deck_code': 'ABCD'})
        data = resp.json()
        self.assertEqual(data['total_cards'], 12)
        self.assertTrue(data['cards'][0]['img_url'].endswith('t_w01_001.png'))
        self.assertEqual(data['cards'][1]['img_url'], '')
