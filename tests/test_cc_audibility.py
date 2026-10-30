import json
import re

import pytest

from learn import audibility_measure as AM
from learn import cc_audibility as C
from learn import local_objective as LO


def _x(ratio=-3.0, vocals=False, others=1, stems=("01_Kick.wav", "09_Bass.wav"), band="BKS", mode="factory"):
    return {"draw": {"ratio_db": ratio, "vocals_drawn": vocals}, "others": [{}] * others, "band": band, "mode": mode,
            "stems": {"v": list(stems) + ["20_LeadVox.wav"], "n": list(stems)}}


def test_the_page_rule():
    assert C.qualifies(_x()) == (True, None)
    assert C.qualifies(_x(ratio=-7.0))[1] == "not exposed"                    # the earlier exposed page's rule
    assert C.qualifies(_x(vocals=True))[1] == "not exposed"
    assert C.qualifies(_x(others=3))[1] == "not exposed"
    assert C.qualifies(_x(stems=("01_Kick.wav",)))[1] == "no drums or no bass in the backing"
    assert C.qualifies(_x(stems=("09_Bass.wav", "25_Organ.wav")))[1] == "no drums or no bass in the backing"
    assert C.qualifies(_x(band="Storm Of Particles"))[1] == "a heavy band"
    assert C.qualifies(_x(mode="wide"))[1] == "an atypical tone (part C's wide draw)"
    assert C.qualifies(_x(mode="start"))[0]
    assert AM.EXPOSED == {"min_ratio_db": -6.0, "vocals": False, "max_others": 2}


def test_backing_classes_read_the_drawn_vocal_variant():
    x = _x(vocals=True)
    assert "vocal" in C.backing_classes(x) and "vocal" not in C.backing_classes(_x())


def test_the_recipe_and_effects_are_the_audibility_pages():
    assert C.N_MAX == 30 and C.SEED != AM.SEED and C.PAGE_SEED != AM.PAGE_SEED
    assert AM.RECIPE == "fresh" and set(AM.EFFECTS) == {"delay", "reverb", "tremolo", "pr12 spring", "sw50r spring"}


def test_renders_are_in_the_machine_cap():
    assert any(re.search(p, "/x/python -u -m learn.cc_audibility render --shard 0/3") for p in LO.RENDERS)
    assert not any(re.search(p, "/x/python -m learn.cc_audibility plan") for p in LO.RENDERS)


def test_runs_refuse_without_the_declaration(tmp_path, monkeypatch):
    led = tmp_path / "ledger.json"
    led.write_text(json.dumps({"tests": [{"test_id": C.LEDGER_ID}]}))
    assert not C.ledger_declared(led)
    led.write_text(json.dumps({"tests": [{"test_id": C.LEDGER_ID, C.LEDGER_KEY: f"{C.LEDGER_MARK} (...)"}]}))
    assert C.ledger_declared(led)
    monkeypatch.setattr(C, "ledger_declared", lambda path=None: False)
    with pytest.raises(SystemExit, match="runs refuse"):
        C.main(["render", "--shard", "0/3"])


def test_flags_belong_to_their_commands():
    with pytest.raises(SystemExit):
        C.main(["plan", "--shard", "1/3"])
    with pytest.raises(SystemExit):
        C.main(["measure", "--force"])
