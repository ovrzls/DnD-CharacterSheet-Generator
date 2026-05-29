"""
Regression tests for step 5 template constant injection.

Guards against the HTML-escaping bug where Jinja2 would render dict values
such as PB_COSTS without |tojson, turning " into &#34; and breaking the
inline <script> block so all constants were undefined in abilities.js.
"""
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from ui.app import app as flask_app


@pytest.fixture
def client():
    flask_app.config["TESTING"] = True
    flask_app.secret_key = "test-secret"
    with flask_app.test_client() as c:
        with c.session_transaction() as sess:
            sess["character"] = {
                "name": "Test Hero",
                "species": "Half-Orc",
                "char_class": "fighter",
                "level": 4,
                "background": "Soldier",
            }
        yield c


def _get_constants_script(body: str) -> str:
    """Extract the inline <script> block that defines server constants."""
    scripts = re.findall(r"<script[^>]*>(.*?)</script>", body, re.DOTALL)
    for s in scripts:
        if "const PB_COSTS" in s:
            return s
    return ""


class TestStep5ConstantInjection:
    def test_page_loads(self, client):
        resp = client.get("/step/5")
        assert resp.status_code == 200

    def test_no_html_escaped_quotes_in_constants_script(self, client):
        body = client.get("/step/5").data.decode("utf-8")
        script = _get_constants_script(body)
        assert script, "Could not find the constants <script> block"
        assert "&#34;" not in script, (
            "HTML-escaped quote (&#34;) found inside <script> — "
            "a Jinja expression is missing | tojson"
        )
        assert "&amp;" not in script, (
            "HTML-escaped ampersand (&amp;) found inside <script>"
        )

    def test_pb_costs_is_parseable_json(self, client):
        body = client.get("/step/5").data.decode("utf-8")
        script = _get_constants_script(body)
        m = re.search(r"const PB_COSTS\s*=\s*({[^;]+});", script)
        assert m, "Could not find PB_COSTS constant"
        costs = json.loads(m.group(1))
        assert costs.get("8") == 0, "PB_COSTS['8'] should be 0"

    def test_racial_bonuses_for_half_orc(self, client):
        body = client.get("/step/5").data.decode("utf-8")
        script = _get_constants_script(body)
        m = re.search(r"const RACIAL_BONUSES\s*=\s*({[^;]+});", script)
        assert m, "Could not find RACIAL_BONUSES constant"
        bonuses = json.loads(m.group(1))
        assert bonuses.get("strength") == 2, "Half-Orc STR bonus should be 2"
        assert bonuses.get("constitution") == 1, "Half-Orc CON bonus should be 1"

    def test_racial_bonuses_for_human(self, client):
        with flask_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["character"] = {
                    "name": "T",
                    "species": "Human", "char_class": "wizard",
                    "level": 1, "background": "Sage",
                }
            body = c.get("/step/5").data.decode("utf-8")
        script = _get_constants_script(body)
        m = re.search(r"const RACIAL_BONUSES\s*=\s*({[^;]+});", script)
        assert m, "Could not find RACIAL_BONUSES constant"
        bonuses = json.loads(m.group(1))
        assert bonuses.get("flexible") == 2, "Human should have 2 flexible slots"
        assert bonuses.get("flexible_amount") == 1

    def test_racial_bonuses_for_half_elf(self, client):
        with flask_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["character"] = {
                    "name": "T",
                    "species": "Half-Elf", "char_class": "sorcerer",
                    "level": 1, "background": "Sage",
                }
            body = c.get("/step/5").data.decode("utf-8")
        script = _get_constants_script(body)
        m = re.search(r"const RACIAL_BONUSES\s*=\s*({[^;]+});", script)
        assert m
        bonuses = json.loads(m.group(1))
        assert bonuses.get("charisma") == 2
        assert bonuses.get("flexible") == 2
        assert bonuses.get("fixed_bonus_abilities") == ["cha"]

    def test_default_method_is_standard_array(self, client):
        """First visit defaults to standard_array so Phase 2 is visible immediately."""
        body = client.get("/step/5").data.decode("utf-8")
        script = _get_constants_script(body)
        m = re.search(r'const SAVED_METHOD\s*=\s*"([^"]+)"', script)
        assert m, "Could not find SAVED_METHOD constant"
        assert m.group(1) == "standard_array"

    def test_asi_slots_earned_is_integer(self, client):
        body = client.get("/step/5").data.decode("utf-8")
        script = _get_constants_script(body)
        m = re.search(r"const ASI_SLOTS_EARNED\s*=\s*(\d+)", script)
        assert m, "Could not find ASI_SLOTS_EARNED"
        # Fighter level 4 → 1 slot
        assert int(m.group(1)) == 1

    def test_roll_confirmed_field_present_with_value_zero_when_no_rolled_scores(self, client):
        body = client.get("/step/5").data.decode("utf-8")
        assert 'id="roll-confirmed-input"' in body
        assert 'value="0"' in body

    def test_roll_confirmed_field_is_one_when_session_has_rolled_scores(self):
        with flask_app.test_client() as c:
            with c.session_transaction() as sess:
                sess["character"] = {
                    "name": "T",
                    "species": "Half-Orc", "char_class": "fighter",
                    "level": 4, "background": "Soldier",
                    "ability_method": "random_roll",
                }
                sess["rolled_scores"] = [17, 15, 14, 13, 10, 8]
            body = c.get("/step/5").data.decode("utf-8")
        assert 'value="1"' in body


class TestRandomRollRoundTrip:
    """Regression for the back-navigation bug where session.pop removed rolled_scores."""

    ROLLED = [17, 15, 14, 13, 10, 8]
    ASSIGNED = {"str": 17, "dex": 15, "con": 14, "int": 13, "wis": 10, "cha": 8}

    def _session_after_step5_submit(self):
        """Return a test client that has already successfully POSTed step 5."""
        c = flask_app.test_client()
        with c.session_transaction() as sess:
            sess["character"] = {
                "name": "T",
                "species": "Half-Orc", "char_class": "fighter",
                "level": 1, "background": "Soldier",
            }
            sess["rolled_scores"] = self.ROLLED

        form_data = {
            "ability_method": "random_roll",
            "roll_confirmed": "1",
            **{f"score_{ab}": str(v) for ab, v in self.ASSIGNED.items()},
            **{f"flex_{ab}": "0" for ab in ["str", "dex", "con", "int", "wis", "cha"]},
        }
        resp = c.post("/step/5", data=form_data, follow_redirects=False)
        assert resp.status_code == 302, f"Step 5 POST should redirect, got {resp.status_code}"
        return c

    def test_rolled_scores_survive_step5_submission(self):
        """rolled_scores must still be in session after a successful step 5 POST."""
        c = self._session_after_step5_submit()
        with c.session_transaction() as sess:
            assert sess.get("rolled_scores") == self.ROLLED, (
                "rolled_scores were prematurely cleared from session on step 5 success"
            )

    def test_step5_get_after_back_nav_serves_rolled_scores(self):
        """GET /step/5 after returning from step 6 should inject ROLLED_SCORES into page."""
        c = self._session_after_step5_submit()
        body = c.get("/step/5").data.decode("utf-8")
        script = _get_constants_script(body)

        m = re.search(r"const ROLLED_SCORES\s*=\s*(\[[^\]]+\]);", script)
        assert m, "ROLLED_SCORES not found in page script"
        rolled = json.loads(m.group(1))
        assert sorted(rolled) == sorted(self.ROLLED), (
            f"ROLLED_SCORES {rolled} does not match expected {self.ROLLED}"
        )

    def test_step5_get_after_back_nav_has_random_roll_method(self):
        c = self._session_after_step5_submit()
        body = c.get("/step/5").data.decode("utf-8")
        script = _get_constants_script(body)
        m = re.search(r'const SAVED_METHOD\s*=\s*"([^"]+)"', script)
        assert m and m.group(1) == "random_roll"

    def test_resubmit_after_back_nav_succeeds(self):
        """Second POST with original rolled scores and session pool still present."""
        c = self._session_after_step5_submit()
        form_data = {
            "ability_method": "random_roll",
            "roll_confirmed": "1",
            **{f"score_{ab}": str(v) for ab, v in self.ASSIGNED.items()},
            **{f"flex_{ab}": "0" for ab in ["str", "dex", "con", "int", "wis", "cha"]},
        }
        resp = c.post("/step/5", data=form_data, follow_redirects=False)
        assert resp.status_code == 302, "Re-submit after back-nav should succeed"
