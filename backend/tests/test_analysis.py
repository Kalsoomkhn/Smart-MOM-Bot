from app.services.analysis import normalize_minutes, reconcile_actions
from app.services.transcription import speaker_turns_to_transcript


def test_normalizes_model_output():
    assert normalize_minutes({"agenda": [" Review progress "], "actions": [{"owner": "", "task": "Run tests", "due": ""}]}) == {
        "agenda": ["Review progress"], "decisions": [], "discussion": [],
        "actions": [{"owner": "Unassigned", "task": "Run tests", "due": "Not specified"}],
    }


def test_grounds_action_owner():
    minutes = {"agenda": [], "decisions": [], "discussion": ["No specific discussion"], "actions": [{"owner": "Speaker 1", "task": "Run tests", "due": "Thursday"}]}
    assert reconcile_actions(minutes, "Speaker 1: Ali will run tests by Thursday.")["actions"][0]["owner"] == "Ali"


def test_parses_speaker_turns():
    result = speaker_turns_to_transcript("[00:00:00.000 --> 00:00:02.000] Hello. [SPEAKER_TURN] [00:00:02.000 --> 00:00:04.000] Welcome.")
    assert result["text"] == "Speaker 1: Hello.\nSpeaker 2: Welcome."
