from typing import Any

from app.core.config import Settings
from app.services.analysis import AnalysisService, normalize_minutes, reconcile_actions
from app.services.transcription import speaker_turns_to_transcript

SCENARIOS: list[dict[str, Any]] = [
    {
        "id": "scenario_1",
        "title": "FYP Software Engineering Sprint & Architecture Review",
        "category": "Engineering & Software Development",
        "raw_dialogue": """[00:00:00.000 --> 00:00:05.000] Dr Tariq: Welcome everyone. Today we need to evaluate the SmartMOM bot architecture and FastAPI migration. [SPEAKER_TURN] [00:00:05.000 --> 00:00:12.000] Kalsoom Khan: I completed the migration of our backend routes to FastAPI and standardized HTTPBearer authentication. [SPEAKER_TURN] [00:00:12.000 --> 00:00:18.000] Bilal: Great work Kalsoom. I will optimize the SQLite and PostgreSQL database session pooling by Friday. [SPEAKER_TURN] [00:00:18.000 --> 00:00:25.000] Kalsoom Khan: Kalsoom will prepare the final supervisor demo script and evaluation metrics by next Tuesday.""",
        "expected_actions_count": 2,
    },
    {
        "id": "scenario_2",
        "title": "Product Strategy & UX Redesign Alignment",
        "category": "Product & User Experience",
        "raw_dialogue": """[00:00:00.000 --> 00:00:04.000] Sarah: Let's review the user feedback on the meeting minutes dashboard. [SPEAKER_TURN] [00:00:04.000 --> 00:00:10.000] Alex: Users love the dark mode, but request a faster one-click PDF export button. [SPEAKER_TURN] [00:00:10.000 --> 00:00:16.000] Sarah: Agreed. We decided to place the export PDF button right next to the transcript header. [SPEAKER_TURN] [00:00:16.000 --> 00:00:22.000] Alex: Alex will update the Figma UI mockups by Wednesday. [SPEAKER_TURN] [00:00:22.000 --> 00:00:28.000] Daniel: Daniel is going to write the user onboarding documentation before the release.""",
        "expected_actions_count": 2,
    },
    {
        "id": "scenario_3",
        "title": "Enterprise Client Requirements & SLA Review",
        "category": "Client Delivery & Compliance",
        "raw_dialogue": """[00:00:00.000 --> 00:00:05.000] David: Thank you Elena for joining. We want to align on enterprise security and RBAC requirements. [SPEAKER_TURN] [00:00:05.000 --> 00:00:12.000] Elena: Security is top priority. We need token-based auth with explicit scopes and role separation. [SPEAKER_TURN] [00:00:12.000 --> 00:00:18.000] Mark: Mark will configure the audit logging pipeline for GDPR compliance by end of month. [SPEAKER_TURN] [00:00:18.000 --> 00:00:24.000] David: We confirmed that the enterprise SLA guarantee will be 99.9% uptime.""",
        "expected_actions_count": 1,
    },
    {
        "id": "scenario_4",
        "title": "DevOps Security & Infrastructure Incident Post-Mortem",
        "category": "DevOps & Infrastructure",
        "raw_dialogue": """[00:00:00.000 --> 00:00:06.000] Omar: Let's analyze yesterday's database connectivity drop during high load. [SPEAKER_TURN] [00:00:06.000 --> 00:00:12.000] Priya: The root cause was stale connection pool handles failing under sudden load spikes. [SPEAKER_TURN] [00:00:12.000 --> 00:00:18.000] Hassan: Hassan must enable pool_pre_ping and automated reconnects in SQLAlchemy by tomorrow morning. [SPEAKER_TURN] [00:00:18.000 --> 00:00:24.000] Priya: Priya will deploy the zero-downtime hotfix patch to production by 4 PM.""",
        "expected_actions_count": 2,
    },
    {
        "id": "scenario_5",
        "title": "Cross-Functional Marketing & Sales Q3 Product Launch",
        "category": "Marketing & Sales Strategy",
        "raw_dialogue": """[00:00:00.000 --> 00:00:05.000] Jessica: Welcome team. Today we map out the SmartMOM Bot public announcement. [SPEAKER_TURN] [00:00:05.000 --> 00:00:11.000] Ryan: Sales leads are requesting a live webinar showcasing automatic action item tracking. [SPEAKER_TURN] [00:00:11.000 --> 00:00:17.000] Chloe: Chloe will draft the promotional email newsletter and blog post by Monday. [SPEAKER_TURN] [00:00:17.000 --> 00:00:23.000] Ryan: Ryan shall coordinate with enterprise trial users for testimonial recording by Friday.""",
        "expected_actions_count": 2,
    },
]


def test_pipeline_scenarios_evaluation() -> None:
    settings = Settings(minutes_provider="local", transcription_provider="local")
    service = AnalysisService(settings)

    results: list[dict[str, Any]] = []
    for scenario in SCENARIOS:
        parsed_transcript = speaker_turns_to_transcript(scenario["raw_dialogue"])
        transcript_text = parsed_transcript["text"]

        assert transcript_text.strip(), (
            f"Transcript parsing failed for {scenario['id']}"
        )

        # Test Sentiment & Engagement analysis
        sentiment_res = service._sentiment(transcript_text)
        assert "overall" in sentiment_res
        assert "participants" in sentiment_res
        assert len(sentiment_res["participants"]) > 0

        # Test rule-based action item reconciliation logic on sample structured output
        sample_minutes = {
            "agenda": [f"Discuss {scenario['title']}"],
            "decisions": ["Approved project roadmap"],
            "discussion": ["Detailed review conducted."],
            "actions": [
                {
                    "owner": "Unassigned",
                    "task": "prepare the final supervisor demo script",
                    "due": "next Tuesday",
                }
            ]
            if scenario["id"] == "scenario_1"
            else [],
        }

        reconciled = reconcile_actions(sample_minutes, transcript_text)
        normalized = normalize_minutes(reconciled)

        if scenario["id"] == "scenario_1":
            assert normalized["actions"][0]["owner"] == "Kalsoom"

        results.append(
            {
                "id": scenario["id"],
                "title": scenario["title"],
                "category": scenario["category"],
                "speakers_count": len(sentiment_res["participants"]),
                "overall_sentiment": sentiment_res["overall"],
                "participants_engagement": [
                    f"{p['name']}: {p['engagement']}% ({p['sentiment']})"
                    for p in sentiment_res["participants"]
                ],
                "action_items_count": len(normalized["actions"]),
            }
        )

    assert len(results) == 5
